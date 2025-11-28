# Sweepzy API Documentation

This document provides comprehensive information about the Sweepzy API endpoints, authentication, and usage examples.

## Base URL

When running locally: `http://localhost:8000`

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### Health Check

**GET** `/health`
- Description: Check if the API is running
- Authentication: Not required
- Response: `{"status": "healthy"}`

### User Management

#### Register User
**POST** `/api/user/register`
- Description: Register a new user account
- Authentication: Not required
- Request Body:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "phone_number": "+1234567890"
}
```

#### Login
**POST** `/api/user/login`
- Description: Authenticate user and get JWT token
- Authentication: Not required
- Request Body:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```
- Response:
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user_id": 123
}
```

#### Get User Profile
**GET** `/api/user/profile`
- Description: Get current user's profile information
- Authentication: Required
- Response:
```json
{
  "id": 123,
  "email": "user@example.com",
  "full_name": "John Doe",
  "points": 150,
  "badges": ["First Report", "Clean Streak"]
}
```

### Litter Reports

#### Create Litter Report
**POST** `/api/litter_reports/`
- Description: Submit a new litter report with image
- Authentication: Required
- Content-Type: `multipart/form-data`
- Request Body:
```
image: [file upload]
latitude: 40.7128
longitude: -74.0060
description: "Plastic bottles near the park"
```

#### Get Litter Reports
**GET** `/api/litter_reports/`
- Description: Get litter reports with optional filtering
- Authentication: Required
- Query Parameters:
  - `latitude`: Center latitude for radius search
  - `longitude`: Center longitude for radius search
  - `radius`: Search radius in kilometers (default: 5)
  - `limit`: Number of results (default: 50)
  - `offset`: Pagination offset (default: 0)

#### Get Single Litter Report
**GET** `/api/litter_reports/{report_id}`
- Description: Get detailed information about a specific report
- Authentication: Required
- Response:
```json
{
  "id": 456,
  "user_id": 123,
  "latitude": 40.7128,
  "longitude": -74.0060,
  "description": "Plastic bottles near the park",
  "image_url": "/uploads/reports/image123.jpg",
  "status": "verified",
  "detection_results": {
    "detected_items": ["plastic_bottle", "food_wrapper"],
    "confidence_scores": [0.95, 0.87]
  },
  "created_at": "2025-11-26T10:30:00Z"
}
```

### Litter Detection

#### Analyze Image
**POST** `/api/litter_detections/analyze`
- Description: Analyze an image for litter detection using AI
- Authentication: Required
- Content-Type: `multipart/form-data`
- Request Body:
```
image: [file upload]
```
- Response:
```json
{
  "detection_id": "det_123",
  "detected_items": [
    {
      "type": "plastic_bottle",
      "confidence": 0.95,
      "bounding_box": [100, 150, 200, 300]
    },
    {
      "type": "food_wrapper",
      "confidence": 0.87,
      "bounding_box": [250, 200, 350, 280]
    }
  ],
  "total_items": 2
}
```

### Cleanup Events

#### Create Cleanup Event
**POST** `/api/cleanup_events/`
- Description: Create a new community cleanup event
- Authentication: Required (Admin/Organizer role)
- Request Body:
```json
{
  "title": "Park Cleanup Day",
  "description": "Join us for a community cleanup at Central Park",
  "location": {
    "latitude": 40.7829,
    "longitude": -73.9654,
    "address": "Central Park, New York, NY"
  },
  "scheduled_date": "2025-12-15T10:00:00Z",
  "max_participants": 50
}
```

#### Get Cleanup Events
**GET** `/api/cleanup_events/`
- Description: Get list of upcoming cleanup events
- Authentication: Required
- Query Parameters:
  - `latitude`: Center latitude for radius search
  - `longitude`: Center longitude for radius search
  - `radius`: Search radius in kilometers (default: 10)
  - `upcoming_only`: Show only future events (default: true)

#### Join Cleanup Event
**POST** `/api/cleanup_events/{event_id}/join`
- Description: Join a cleanup event
- Authentication: Required
- Response:
```json
{
  "message": "Successfully joined the event",
  "event_id": 789,
  "participant_count": 25
}
```

### User Dashboard

#### Get User Stats
**GET** `/api/dashboard/stats`
- Description: Get user statistics and achievements
- Authentication: Required
- Response:
```json
{
  "total_reports": 15,
  "verified_reports": 12,
  "total_points": 480,
  "rank": 42,
  "badges": [
    {
      "name": "First Report",
      "description": "Submitted your first litter report",
      "earned_date": "2025-11-01T12:00:00Z"
    }
  ],
  "cleanup_events_attended": 3,
  "items_cleaned": 47
}
```

#### Get Leaderboard
**GET** `/api/dashboard/leaderboard`
- Description: Get community leaderboard
- Authentication: Required
- Query Parameters:
  - `period`: Time period ('week', 'month', 'all_time')
  - `limit`: Number of users to return (default: 10)
- Response:
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "user_name": "EcoWarrior123",
      "points": 1250,
      "reports_count": 45
    },
    {
      "rank": 2,
      "user_name": "CleanCityHero",
      "points": 980,
      "reports_count": 32
    }
  ],
  "user_rank": 42,
  "user_points": 480
}
```

### Badges

#### Get Available Badges
**GET** `/api/badges/`
- Description: Get list of all available badges and requirements
- Authentication: Required
- Response:
```json
[
  {
    "id": 1,
    "name": "First Report",
    "description": "Submit your first litter report",
    "icon_url": "/static/badges/first_report.png",
    "requirements": {
      "reports_count": 1
    }
  },
  {
    "id": 2,
    "name": "Clean Streak",
    "description": "Submit reports for 7 consecutive days",
    "icon_url": "/static/badges/clean_streak.png",
    "requirements": {
      "consecutive_days": 7
    }
  }
]
```

### Notifications

#### Get User Notifications
**GET** `/api/notifications/`
- Description: Get user's notifications
- Authentication: Required
- Query Parameters:
  - `unread_only`: Show only unread notifications (default: false)
  - `limit`: Number of notifications (default: 20)

#### Mark Notification as Read
**PUT** `/api/notifications/{notification_id}/read`
- Description: Mark a notification as read
- Authentication: Required

### Image Upload

#### Upload Image
**POST** `/api/uploads/image`
- Description: Upload an image file
- Authentication: Required
- Content-Type: `multipart/form-data`
- Request Body:
```
file: [image file]
purpose: "litter_report" | "profile_picture" | "cleanup_event"
```
- Response:
```json
{
  "file_url": "/uploads/images/abc123.jpg",
  "file_id": "img_abc123",
  "file_size": 245760,
  "mime_type": "image/jpeg"
}
```

## Error Responses

The API uses standard HTTP status codes and returns error details in the following format:

```json
{
  "error": "Invalid request",
  "message": "The provided email address is already registered",
  "code": "EMAIL_EXISTS"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **General endpoints**: 100 requests per minute per user
- **Image upload**: 10 requests per minute per user
- **AI analysis**: 20 requests per minute per user

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Webhooks

Sweepzy supports webhooks for real-time notifications of important events:

### Available Events

- `report.created`: New litter report submitted
- `report.verified`: Report verified by admin
- `cleanup_event.created`: New cleanup event created
- `user.badge_earned`: User earned a new badge

### Webhook Payload Example

```json
{
  "event": "report.verified",
  "timestamp": "2025-11-26T10:30:00Z",
  "data": {
    "report_id": 456,
    "user_id": 123,
    "points_awarded": 25
  }
}
```

## Support

For API support and questions:
- Email: team.sweepzy@gmail.com

## Changelog

### v1.0.0 (2025-11-26)
- Initial API release
- User authentication and management
- Litter reporting with AI detection
- Cleanup events management
- Gamification features (badges, points, leaderboard)
- Real-time notifications