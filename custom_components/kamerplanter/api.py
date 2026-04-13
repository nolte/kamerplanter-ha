"""API client for communicating with the Kamerplanter backend."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession


_LOGGER = logging.getLogger(__name__)


class KamerplanterApiError(Exception):
    """Base exception for API errors."""


class KamerplanterAuthError(KamerplanterApiError):
    """Authentication error."""


class KamerplanterConnectionError(KamerplanterApiError):
    """Connection error."""


@dataclass
class KamerplanterApi:
    """Client for the Kamerplanter REST API."""

    base_url: str
    session: ClientSession
    api_key: str | None = None
    tenant_slug: str | None = None

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def _tenant_prefix(self) -> str:
        if self.tenant_slug:
            return f"/api/v1/t/{self.tenant_slug}"
        return "/api/v1"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            async with self.session.request(
                method, url, headers=self._headers, **kwargs
            ) as resp:
                if resp.status == 401:
                    raise KamerplanterAuthError("API key invalid or revoked")
                if resp.status == 403:
                    raise KamerplanterAuthError("Insufficient permissions")
                resp.raise_for_status()
                return await resp.json()
        except KamerplanterApiError:
            raise
        except ClientResponseError as err:
            raise KamerplanterConnectionError(
                f"HTTP {err.status} from Kamerplanter at {url}"
            ) from err
        except ClientError as err:
            raise KamerplanterConnectionError(
                f"Cannot connect to Kamerplanter at {self.base_url}"
            ) from err

    async def async_get_health(self) -> dict[str, Any]:
        """Check backend health and retrieve version info."""
        return await self._request("GET", "/api/health")

    async def async_get_current_user(self) -> dict[str, Any]:
        """Validate credentials by fetching current user."""
        return await self._request("GET", "/api/v1/users/me")

    async def async_get_tenants(self) -> list[dict[str, Any]]:
        """Fetch tenants for the authenticated user."""
        return await self._request("GET", "/api/v1/tenants/")

    async def async_get_plants(self) -> list[dict[str, Any]]:
        """Fetch all plant instances."""
        return await self._request("GET", f"{self._tenant_prefix}/plant-instances")

    async def async_get_plant_phase_history(
        self, plant_key: str
    ) -> list[dict[str, Any]]:
        """Fetch phase history for a plant instance (non-tenant-scoped)."""
        return await self._request(
            "GET", f"/api/v1/plant-instances/{plant_key}/phases/history"
        )

    async def async_get_sites(self) -> list[dict[str, Any]]:
        """Fetch all sites (top-level locations)."""
        return await self._request("GET", f"{self._tenant_prefix}/sites")

    async def async_get_locations(self, site_key: str) -> list[dict[str, Any]]:
        """Fetch locations for a site."""
        return await self._request(
            "GET", f"{self._tenant_prefix}/locations", params={"site_key": site_key}
        )

    async def async_get_location_tree(self, site_key: str) -> list[dict[str, Any]]:
        """Fetch full location tree for a site."""
        return await self._request(
            "GET", f"{self._tenant_prefix}/sites/{site_key}/location-tree"
        )

    async def async_get_all_locations(self) -> list[dict[str, Any]]:
        """Fetch all locations across all sites (including nested children)."""
        sites = await self.async_get_sites()
        all_locations: list[dict[str, Any]] = []
        for site in sites:
            site_key = site.get("key") or site.get("_key", "")
            if not site_key:
                continue
            # Fetch tree nodes and flatten
            tree = await self.async_get_location_tree(site_key)
            # Also fetch flat details for full field set
            top_level = await self.async_get_locations(site_key)
            detail_by_key = {loc.get("key", ""): loc for loc in top_level}
            # Collect all child keys from tree, then fetch their details
            child_keys: list[str] = []
            self._collect_child_keys(tree, child_keys)
            for ck in child_keys:
                try:
                    child_locs = await self.async_get_locations_by_parent(site_key, ck)
                    for cl in child_locs:
                        detail_by_key[cl.get("key", "")] = cl
                except KamerplanterApiError:
                    pass
            # Flatten tree to get all keys, then return details
            flat_keys: list[str] = []
            self._flatten_tree_keys(tree, flat_keys)
            for key in flat_keys:
                if key in detail_by_key:
                    all_locations.append(detail_by_key[key])
                else:
                    # Fallback: use tree node data (fewer fields)
                    node = self._find_tree_node(tree, key)
                    if node:
                        node["site_key"] = site_key
                        all_locations.append(node)
        return all_locations

    async def async_get_locations_by_parent(
        self, site_key: str, parent_key: str
    ) -> list[dict[str, Any]]:
        """Fetch child locations for a parent location."""
        return await self._request(
            "GET",
            f"{self._tenant_prefix}/locations",
            params={"site_key": site_key, "parent_location_key": parent_key},
        )

    @staticmethod
    def _collect_child_keys(
        nodes: list[dict[str, Any]], parent_keys: list[str]
    ) -> None:
        """Collect keys of nodes that have children."""
        for node in nodes:
            children = node.get("children", [])
            if children:
                parent_keys.append(node.get("key", ""))
                KamerplanterApi._collect_child_keys(children, parent_keys)

    @staticmethod
    def _flatten_tree_keys(nodes: list[dict[str, Any]], keys: list[str]) -> None:
        """Flatten tree to a list of all keys."""
        for node in nodes:
            key = node.get("key", "")
            if key:
                keys.append(key)
            KamerplanterApi._flatten_tree_keys(node.get("children", []), keys)

    @staticmethod
    def _find_tree_node(nodes: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        """Find a node by key in a tree."""
        for node in nodes:
            if node.get("key") == key:
                return node
            found = KamerplanterApi._find_tree_node(node.get("children", []), key)
            if found:
                return found
        return None

    async def async_get_plant_nutrient_plan(
        self, plant_key: str
    ) -> dict[str, Any] | None:
        """Fetch the nutrient plan assigned to a plant instance."""
        try:
            return await self._request(
                "GET",
                f"{self._tenant_prefix}/plant-instances/{plant_key}/nutrient-plan",
            )
        except KamerplanterApiError:
            return None

    async def async_get_run_nutrient_plan(self, run_key: str) -> dict[str, Any] | None:
        """Fetch the nutrient plan assigned to a planting run."""
        try:
            result = await self._request(
                "GET", f"{self._tenant_prefix}/planting-runs/{run_key}/nutrient-plan"
            )
            return result.get("plan") if result else None
        except KamerplanterApiError:
            return None

    async def async_get_plant_current_dosages(
        self, plant_key: str, current_week: int
    ) -> dict[str, Any] | None:
        """Fetch current dosages for a plant instance."""
        try:
            result = await self._request(
                "GET",
                f"{self._tenant_prefix}/plant-instances/{plant_key}/current-dosages",
                params={"current_week": current_week},
            )
            if result and "message" not in result:
                return result
            return None
        except KamerplanterApiError:
            return None

    async def async_get_plant_active_channels(
        self, plant_key: str, current_week: int
    ) -> list[dict[str, Any]]:
        """Fetch active delivery channels for a plant instance."""
        try:
            return await self._request(
                "GET",
                f"{self._tenant_prefix}/plant-instances/{plant_key}/active-channels",
                params={"current_week": current_week},
            )
        except KamerplanterApiError:
            return []

    async def async_get_run_active_channels(
        self, run_key: str, current_week: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch active delivery channels for a planting run."""
        try:
            params: dict[str, Any] = {}
            if current_week is not None:
                params["current_week"] = current_week
            return await self._request(
                "GET",
                f"{self._tenant_prefix}/planting-runs/{run_key}/active-channels",
                params=params or None,
            )
        except KamerplanterApiError:
            return []

    async def async_get_plan_phase_entries(self, plan_key: str) -> list[dict[str, Any]]:
        """Fetch phase entries for a nutrient plan."""
        try:
            return await self._request(
                "GET", f"{self._tenant_prefix}/nutrient-plans/{plan_key}/entries"
            )
        except KamerplanterApiError:
            return []

    async def async_get_run_phase_timeline(self, run_key: str) -> list[dict[str, Any]]:
        """Fetch phase timeline for a planting run."""
        try:
            return await self._request(
                "GET", f"{self._tenant_prefix}/planting-runs/{run_key}/phase-timeline"
            )
        except KamerplanterApiError:
            return []

    async def async_get_fertilizers(self) -> list[dict[str, Any]]:
        """Fetch all fertilizers (for name lookup)."""
        return await self._request(
            "GET", f"{self._tenant_prefix}/fertilizers", params={"limit": 200}
        )

    async def async_get_planting_runs(self) -> list[dict[str, Any]]:
        """Fetch all planting runs."""
        return await self._request("GET", f"{self._tenant_prefix}/planting-runs")

    async def async_get_pending_tasks(self) -> list[dict[str, Any]]:
        """Fetch pending tasks."""
        return await self._request(
            "GET", f"{self._tenant_prefix}/tasks", params={"status": "pending"}
        )

    async def async_get_runs_by_location(
        self, location_key: str
    ) -> list[dict[str, Any]]:
        """Fetch planting runs assigned to a location."""
        return await self._request(
            "GET",
            f"{self._tenant_prefix}/planting-runs",
            params={"location_key": location_key},
        )

    async def async_get_plant_instances_by_location(
        self, location_key: str
    ) -> list[dict[str, Any]]:
        """Fetch plant instances at slots belonging to a location."""
        try:
            slots = await self._request(
                "GET",
                f"{self._tenant_prefix}/slots",
                params={"location_key": location_key},
            )
            plants: list[dict[str, Any]] = []
            all_plants = await self.async_get_plants()
            slot_keys = {s.get("key") or s.get("_key", "") for s in slots}
            for p in all_plants:
                if p.get("slot_key") in slot_keys and not p.get("removed_on"):
                    plants.append(p)
            return plants
        except KamerplanterApiError:
            return []

    async def async_get_run_watering_schedule(
        self, run_key: str, days_ahead: int = 14
    ) -> dict[str, Any]:
        """Fetch watering schedule for a planting run."""
        return await self._request(
            "GET",
            f"{self._tenant_prefix}/planting-runs/{run_key}/watering-schedule",
            params={"days_ahead": days_ahead},
        )

    async def async_get_care_dashboard(self) -> list[dict[str, Any]]:
        """Fetch care dashboard entries (due dates per plant and reminder type)."""
        return await self._request(
            "GET", f"{self._tenant_prefix}/care-reminders/dashboard"
        )

    async def async_get_overdue_tasks(self) -> list[dict[str, Any]]:
        """Fetch overdue tasks."""
        return await self._request("GET", f"{self._tenant_prefix}/tasks/overdue")

    async def async_complete_task(self, task_key: str) -> dict[str, Any]:
        """Mark a task as completed via the complete endpoint."""
        return await self._request(
            "POST",
            f"{self._tenant_prefix}/tasks/{task_key}/complete",
            json={},
        )

    async def async_get_tanks(self) -> list[dict[str, Any]]:
        """Fetch all tanks."""
        return await self._request("GET", f"{self._tenant_prefix}/tanks")

    async def async_fill_tank(
        self, tank_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Record a tank fill event."""
        return await self._request(
            "POST",
            f"{self._tenant_prefix}/tanks/{tank_key}/fills",
            json=payload,
        )

    async def async_get_tank_active_plans(self, tank_key: str) -> list[dict[str, Any]]:
        """Fetch active nutrient plans for a tank."""
        try:
            return await self._request(
                "GET", f"{self._tenant_prefix}/tanks/{tank_key}/active-nutrient-plans"
            )
        except KamerplanterApiError:
            return []

    async def async_get_tank_latest_fill(self, tank_key: str) -> dict[str, Any] | None:
        """Fetch the latest fill event for a tank."""
        try:
            return await self._request(
                "GET", f"{self._tenant_prefix}/tanks/{tank_key}/fills/latest"
            )
        except KamerplanterApiError:
            return None

    async def async_create_watering_log(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a watering log entry."""
        return await self._request(
            "POST",
            f"{self._tenant_prefix}/watering-logs",
            json=payload,
        )

    async def async_get_tank_sensors(self, tank_key: str) -> list[dict[str, Any]]:
        """Fetch HA sensor mappings linked to a tank."""
        try:
            return await self._request(
                "GET", f"{self._tenant_prefix}/tanks/{tank_key}/sensors"
            )
        except KamerplanterApiError:
            return []

    # --- Growth phases ---

    async def async_get_growth_phase(self, phase_key: str) -> dict[str, Any] | None:
        """Fetch a single growth phase by key."""
        try:
            return await self._request("GET", f"/api/v1/growth-phases/{phase_key}")
        except KamerplanterApiError:
            return None

    # --- Care reminders (REQ-022) ---

    async def async_get_care_profile(self, plant_key: str) -> dict[str, Any] | None:
        """Fetch care profile for a plant (auto-created if missing)."""
        try:
            return await self._request(
                "GET", f"/api/v1/care-reminders/plants/{plant_key}/profile"
            )
        except KamerplanterApiError:
            return None

    async def async_get_care_history(
        self, plant_key: str, reminder_type: str = "watering", limit: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch care confirmation history for a plant."""
        try:
            return await self._request(
                "GET",
                f"/api/v1/care-reminders/plants/{plant_key}/history",
                params={"reminder_type": reminder_type, "limit": limit},
            )
        except KamerplanterApiError:
            return []

    # --- Notification endpoints (REQ-030) ---

    async def async_get_notifications(
        self, limit: int = 50, unread_only: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch notifications for the current user."""
        params: dict[str, Any] = {"limit": limit}
        if unread_only:
            params["unread_only"] = "true"
        return await self._request(
            "GET", f"{self._tenant_prefix}/notifications/", params=params
        )

    async def async_get_notification_count(self) -> int:
        """Fetch unread notification count."""
        result = await self._request(
            "GET", f"{self._tenant_prefix}/notifications/count"
        )
        return int(result.get("count", 0))

    async def async_confirm_care_reminder(
        self, notification_key: str, action: str = "confirmed"
    ) -> dict[str, Any]:
        """Confirm a care reminder notification via actionable button."""
        return await self._request(
            "POST",
            f"{self._tenant_prefix}/notifications/{notification_key}/act",
            params={"action_id": f"confirm_{action}"},
            json={"action": action},
        )

    async def async_mark_notification_read(
        self, notification_key: str
    ) -> dict[str, Any]:
        """Mark a notification as read."""
        return await self._request(
            "POST",
            f"{self._tenant_prefix}/notifications/{notification_key}/read",
            json={},
        )
