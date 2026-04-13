"""
Tests for restocking API endpoints.
"""
import pytest

import mock_data


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Reset in-memory restock orders before each test for isolation."""
    mock_data.restock_orders.clear()
    yield
    mock_data.restock_orders.clear()


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_get_all_recommendations(self, client):
        """Test getting recommendations with default budget."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "sku" in first
        assert "item_name" in first
        assert "current_stock" in first
        assert "forecasted_demand" in first
        assert "shortage" in first
        assert "unit_cost" in first
        assert "recommended_qty" in first
        assert "line_cost" in first
        assert "lead_time_days" in first
        assert "trend" in first
        assert "selected" in first

    def test_recommendation_field_types(self, client):
        """Test that recommendation fields have proper types."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            assert isinstance(rec["current_stock"], int)
            assert isinstance(rec["forecasted_demand"], int)
            assert isinstance(rec["shortage"], int)
            assert isinstance(rec["unit_cost"], (int, float))
            assert isinstance(rec["line_cost"], (int, float))
            assert isinstance(rec["lead_time_days"], int)
            assert isinstance(rec["selected"], bool)
            assert rec["shortage"] >= 0
            assert rec["unit_cost"] >= 0
            assert rec["lead_time_days"] >= 0

    def test_shortage_calculation(self, client):
        """Test that shortage = max(0, forecast - stock)."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            expected = max(0, rec["forecasted_demand"] - rec["current_stock"])
            assert rec["shortage"] == expected
            assert rec["recommended_qty"] == rec["shortage"]

    def test_line_cost_calculation(self, client):
        """Test that line_cost = recommended_qty * unit_cost."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for rec in data:
            expected = rec["recommended_qty"] * rec["unit_cost"]
            assert abs(rec["line_cost"] - expected) < 0.01

    def test_priority_ordering(self, client):
        """Test that increasing-trend items come first, then by shortage desc."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        seen_non_increasing = False
        for rec in data:
            if rec["trend"] == "increasing":
                assert not seen_non_increasing, "increasing items must come first"
            else:
                seen_non_increasing = True

    def test_greedy_selection_respects_budget(self, client):
        """Test that selected items' total cost never exceeds the budget."""
        budget = 25000
        response = client.get(f"/api/restocking/recommendations?budget={budget}")
        data = response.json()

        selected_total = sum(r["line_cost"] for r in data if r["selected"])
        assert selected_total <= budget

    def test_zero_budget_selects_nothing(self, client):
        """Test that a $0 budget yields no selected items."""
        response = client.get("/api/restocking/recommendations?budget=0")
        data = response.json()

        for rec in data:
            assert rec["selected"] is False

    def test_large_budget_selects_all_shortages(self, client):
        """Test that a very large budget selects every item with a shortage."""
        response = client.get("/api/restocking/recommendations?budget=1000000")
        data = response.json()

        for rec in data:
            if rec["shortage"] > 0:
                assert rec["selected"] is True
            else:
                assert rec["selected"] is False

    def test_trend_values(self, client):
        """Test that trend values are valid."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        valid_trends = ["increasing", "stable", "decreasing"]
        for rec in data:
            assert rec["trend"] in valid_trends


class TestRestockingOrders:
    """Test suite for POST and GET /api/restocking/orders."""

    def _sample_items(self):
        return [
            {
                "sku": "FLT-405",
                "item_name": "Oil Filter Cartridge",
                "quantity": 540,
                "unit_cost": 12.0,
                "line_cost": 6480.0,
                "lead_time_days": 3,
            },
            {
                "sku": "GSK-203",
                "item_name": "High-Temperature Gasket",
                "quantity": 280,
                "unit_cost": 8.75,
                "line_cost": 2450.0,
                "lead_time_days": 4,
            },
        ]

    def test_list_orders_initially_empty(self, client):
        """Test that orders list is empty before any submission."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order(self, client):
        """Test creating a restock order returns proper structure."""
        payload = {"budget": 25000, "items": self._sample_items()}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert "id" in order
        assert order["id"].startswith("RST-")
        assert "submitted_at" in order
        assert order["budget"] == 25000
        assert abs(order["total_cost"] - 8930.0) < 0.01
        assert len(order["items"]) == 2
        assert order["status"] == "submitted"
        assert order["max_lead_time_days"] == 4
        assert "expected_delivery" in order

    def test_created_order_appears_in_list(self, client):
        """Test that a created order appears in GET /api/restocking/orders."""
        payload = {"budget": 25000, "items": self._sample_items()}
        client.post("/api/restocking/orders", json=payload)

        response = client.get("/api/restocking/orders")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "RST-0001"

    def test_orders_returned_newest_first(self, client):
        """Test that orders are returned newest first."""
        payload = {"budget": 25000, "items": self._sample_items()}
        client.post("/api/restocking/orders", json=payload)
        client.post("/api/restocking/orders", json=payload)

        response = client.get("/api/restocking/orders")
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "RST-0002"
        assert data[1]["id"] == "RST-0001"

    def test_create_order_over_budget_rejected(self, client):
        """Test that an order exceeding budget returns 400."""
        payload = {"budget": 1000, "items": self._sample_items()}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "budget" in data["detail"].lower()

    def test_create_order_empty_items_rejected(self, client):
        """Test that an order with no items returns 400."""
        payload = {"budget": 25000, "items": []}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_order_item_structure(self, client):
        """Test that order items have proper structure."""
        payload = {"budget": 25000, "items": self._sample_items()}
        response = client.post("/api/restocking/orders", json=payload)
        order = response.json()

        for item in order["items"]:
            assert "sku" in item
            assert "item_name" in item
            assert "quantity" in item
            assert "unit_cost" in item
            assert "line_cost" in item
            assert "lead_time_days" in item
            assert isinstance(item["quantity"], int)
            assert isinstance(item["unit_cost"], (int, float))
