"""Tests for EV Tracker integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.evtracker import (
    async_remove_entry,
    async_setup_entry,
    async_unload_entry,
    async_update_options,
)
from custom_components.evtracker.const import (
    DOMAIN,
)


class TestAsyncSetupEntry:
    """Test async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
        mock_state_response: dict,
    ):
        """Test successful setup."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.evtracker.async_get_clientsession") as mock_get_session,
            patch("custom_components.evtracker.EVTrackerAPI") as mock_api_class,
            patch(
                "custom_components.evtracker.EVTrackerDataUpdateCoordinator"
            ) as mock_coordinator_class,
            patch("custom_components.evtracker.async_setup_services") as mock_setup_services,
            patch.object(hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock),
        ):
            # Setup mocks
            mock_get_session.return_value = MagicMock()
            mock_api_class.return_value = AsyncMock()

            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            # Run setup
            result = await async_setup_entry(hass, entry)

            assert result is True
            assert DOMAIN in hass.data
            assert entry.entry_id in hass.data[DOMAIN]
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            mock_setup_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_services_only_once(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
        mock_state_response: dict,
    ):
        """Test that services are only set up once for multiple entries."""
        entries = []
        for i in range(2):
            entry = MockConfigEntry(
                domain=DOMAIN,
                title=f"EV Tracker - Test {i}",
                data=mock_config_entry_data,
                unique_id=f"{DOMAIN}_{123 + i}",
            )
            entry.add_to_hass(hass)
            entries.append(entry)

        with (
            patch("custom_components.evtracker.async_get_clientsession"),
            patch("custom_components.evtracker.EVTrackerAPI"),
            patch(
                "custom_components.evtracker.EVTrackerDataUpdateCoordinator"
            ) as mock_coordinator_class,
            patch("custom_components.evtracker.async_setup_services") as mock_setup_services,
            patch.object(hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock),
        ):
            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            # Setup first entry
            await async_setup_entry(hass, entries[0])
            assert mock_setup_services.call_count == 1

            # Setup second entry
            await async_setup_entry(hass, entries[1])
            # Services should not be called again
            assert mock_setup_services.call_count == 1


class TestAsyncUnloadEntry:
    """Test async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
    ):
        """Test successful unload."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        hass.data[DOMAIN] = {entry.entry_id: MagicMock()}

        with (
            patch.object(
                hass.config_entries,
                "async_unload_platforms",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("custom_components.evtracker.async_unload_services") as mock_unload_services,
        ):
            result = await async_unload_entry(hass, entry)

            assert result is True
            assert entry.entry_id not in hass.data[DOMAIN]
            mock_unload_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_entry_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
    ):
        """Test failed unload."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        hass.data[DOMAIN] = {entry.entry_id: MagicMock()}

        with (
            patch.object(
                hass.config_entries,
                "async_unload_platforms",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch("custom_components.evtracker.async_unload_services") as mock_unload_services,
        ):
            result = await async_unload_entry(hass, entry)

            assert result is False
            # Coordinator should still be there on failure
            assert entry.entry_id in hass.data[DOMAIN]
            mock_unload_services.assert_not_called()


class TestAsyncUpdateOptions:
    """Test async_update_options."""

    @pytest.mark.asyncio
    async def test_update_options_reloads_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
    ):
        """Test that options update reloads entry."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        with patch.object(
            hass.config_entries,
            "async_reload",
            new_callable=AsyncMock,
        ) as mock_reload:
            await async_update_options(hass, entry)

            mock_reload.assert_called_once_with(entry.entry_id)


class TestAsyncRemoveEntry:
    """Test async_remove_entry."""

    @pytest.mark.asyncio
    async def test_remove_entry_logs(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
    ):
        """Test that entry removal is logged."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        # Should not raise
        await async_remove_entry(hass, entry)


class TestPlatforms:
    """Test platform setup."""

    @pytest.mark.asyncio
    async def test_platforms_are_forwarded(
        self,
        hass: HomeAssistant,
        mock_config_entry_data: dict,
    ):
        """Test that platforms are forwarded during setup."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.evtracker.async_get_clientsession"),
            patch("custom_components.evtracker.EVTrackerAPI"),
            patch(
                "custom_components.evtracker.EVTrackerDataUpdateCoordinator"
            ) as mock_coordinator_class,
            patch("custom_components.evtracker.async_setup_services"),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ) as mock_forward,
        ):
            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(hass, entry)

            # Check platforms were forwarded
            mock_forward.assert_called_once()
            call_args = mock_forward.call_args
            platforms = call_args[0][1]
            assert "sensor" in [str(p) for p in platforms]
            assert "binary_sensor" in [str(p) for p in platforms]
