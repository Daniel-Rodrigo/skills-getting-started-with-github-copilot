"""
Test suite for the Mergington High School Activities API

Tests cover all endpoints including:
- Getting all activities
- Signing up for activities
- Unregistering from activities
- Error handling for edge cases
"""

import pytest
from fastapi.testclient import TestClient
from app import app, activities

# Create test client
client = TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self):
        """Test successfully retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_contains_all_fields(self):
        """Test that returned activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
    
    def test_get_activities_participants_list(self):
        """Test that participants are returned as a list"""
        response = client.get("/activities")
        data = response.json()
        
        assert isinstance(data["Chess Club"]["participants"], list)
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self):
        """Test successfully signing up for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant(self):
        """Test that signup actually adds the student to participants"""
        email = "testuser@mergington.edu"
        client.post(
            "/activities/Drama Club/signup",
            params={"email": email}
        )
        
        response = client.get("/activities")
        assert email in response.json()["Drama Club"]["participants"]
    
    def test_signup_activity_not_found(self):
        """Test signup to non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_email(self):
        """Test signup with email already signed up for activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}  # Already signed up
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_missing_email_parameter(self):
        """Test signup without email parameter"""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_signup_multiple_activities(self):
        """Test that same student can sign up for multiple activities"""
        email = "multi_activity@mergington.edu"
        
        # First activity
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second activity
        response2 = client.post(
            "/activities/Drama Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups
        response3 = client.get("/activities")
        activities_data = response3.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Drama Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_success(self):
        """Test successfully unregistering from an activity"""
        email = "unregister_test@mergington.edu"
        
        # First sign up
        client.post(
            "/activities/Art Studio/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Art Studio/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Art Studio" in data["message"]
    
    def test_unregister_removes_participant(self):
        """Test that unregister actually removes the student"""
        email = "remove_test@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Science Club/signup",
            params={"email": email}
        )
        
        # Get initial count
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Science Club"]["participants"])
        
        # Unregister
        client.delete(
            "/activities/Science Club/signup",
            params={"email": email}
        )
        
        # Verify removal
        response2 = client.get("/activities")
        final_count = len(response2.json()["Science Club"]["participants"])
        assert final_count == initial_count - 1
        assert email not in response2.json()["Science Club"]["participants"]
    
    def test_unregister_activity_not_found(self):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Fake Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_email_not_signed_up(self):
        """Test unregister when email is not signed up"""
        response = client.delete(
            "/activities/Basketball Team/signup",
            params={"email": "notstudent@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_missing_email_parameter(self):
        """Test unregister without email parameter"""
        response = client.delete("/activities/Soccer Club/signup")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_unregister_twice_same_email(self):
        """Test attempting to unregister same email twice"""
        email = "double_unregister@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        
        # First unregister (should succeed)
        response1 = client.delete(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second unregister (should fail)
        response2 = client.delete(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "not signed up" in data["detail"]


class TestIntegrationScenarios:
    """Integration tests for combined operations"""
    
    def test_full_signup_and_unregister_flow(self):
        """Test complete flow: get activities, sign up, unregister"""
        email = "integration_test@mergington.edu"
        activity = "Gym Class"
        
        # Step 1: Get activities
        response1 = client.get("/activities")
        assert response1.status_code == 200
        initial_participants = len(response1.json()[activity]["participants"])
        
        # Step 2: Sign up
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Step 3: Verify signup
        response3 = client.get("/activities")
        assert len(response3.json()[activity]["participants"]) == initial_participants + 1
        
        # Step 4: Unregister
        response4 = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response4.status_code == 200
        
        # Step 5: Verify unregister
        response5 = client.get("/activities")
        assert len(response5.json()[activity]["participants"]) == initial_participants
