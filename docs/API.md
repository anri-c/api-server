# API Documentation

This document provides detailed information about the API endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses JWT (JSON Web Token) authentication with LINE OAuth integration.

### Authentication Flow

1. **Redirect to LINE OAuth**
   ```
   https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state={STATE}&scope=profile%20openid
   ```

2. **Handle OAuth Callback**
   ```http
   POST /auth/line/callback
   Content-Type: application/json
   
   {
     "access_token": "LINE_ACCESS_TOKEN"
   }
   ```

3. **Use JWT Token**
   ```http
   Authorization: Bearer {JWT_TOKEN}
   ```

## Endpoints

### Health Check

#### GET /api/health

Check API health status.

**Request:**
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-16T12:00:00Z",
  "version": "1.0.0"
}
```

### Authentication

#### POST /auth/line/callback

Handle LINE OAuth callback and generate JWT token.

**Request:**
```http
POST /auth/line/callback
Content-Type: application/json

{
  "access_token": "LINE_ACCESS_TOKEN_FROM_OAUTH"
}
```

**Response (Success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "line_user_id": "U1234567890abcdef",
    "display_name": "John Doe",
    "picture_url": "https://profile.line-scdn.net/...",
    "email": "john@example.com",
    "created_at": "2025-09-16T12:00:00Z"
  }
}
```

**Response (Error):**
```json
{
  "error": "invalid_token",
  "error_description": "The provided access token is invalid"
}
```

### Items

#### GET /api/items/

Get paginated list of user's items with optional filtering and sorting.

**Request:**
```http
GET /api/items/?page=1&page_size=20&search=laptop&min_price=100&max_price=1000&sort_by=created_at&sort_order=desc
Authorization: Bearer {JWT_TOKEN}
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `search` (optional): Search term for item name/description
- `min_price` (optional): Minimum price filter
- `max_price` (optional): Maximum price filter
- `sort_by` (optional): Sort field (`name`, `price`, `created_at`)
- `sort_order` (optional): Sort order (`asc`, `desc`)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Gaming Laptop",
      "description": "High-performance gaming laptop",
      "price": "999.99",
      "user_id": 1,
      "created_at": "2025-09-16T12:00:00Z",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

#### POST /api/items/

Create a new item.

**Request:**
```http
POST /api/items/
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json

{
  "name": "Gaming Laptop",
  "description": "High-performance gaming laptop with RTX 4080",
  "price": "1299.99"
}
```

**Response (Success):**
```json
{
  "id": 1,
  "name": "Gaming Laptop",
  "description": "High-performance gaming laptop with RTX 4080",
  "price": "1299.99",
  "user_id": 1,
  "created_at": "2025-09-16T12:00:00Z",
  "updated_at": null
}
```

**Response (Validation Error):**
```json
{
  "error": "validation_error",
  "message": "Item name cannot be empty",
  "details": [
    {
      "field": "name",
      "message": "String should have at least 1 character"
    }
  ]
}
```

#### GET /api/items/{id}

Get a specific item by ID.

**Request:**
```http
GET /api/items/1
Authorization: Bearer {JWT_TOKEN}
```

**Response (Success):**
```json
{
  "id": 1,
  "name": "Gaming Laptop",
  "description": "High-performance gaming laptop",
  "price": "1299.99",
  "user_id": 1,
  "created_at": "2025-09-16T12:00:00Z",
  "updated_at": null
}
```

**Response (Not Found):**
```json
{
  "error": "item_not_found",
  "message": "Item with id 1 not found"
}
```

**Response (Access Denied):**
```json
{
  "error": "access_denied",
  "message": "User 2 does not have access to item 1"
}
```

#### PUT /api/items/{id}

Update an existing item.

**Request:**
```http
PUT /api/items/1
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json

{
  "name": "Updated Gaming Laptop",
  "price": "1199.99"
}
```

**Response (Success):**
```json
{
  "id": 1,
  "name": "Updated Gaming Laptop",
  "description": "High-performance gaming laptop",
  "price": "1199.99",
  "user_id": 1,
  "created_at": "2025-09-16T12:00:00Z",
  "updated_at": "2025-09-16T13:00:00Z"
}
```

#### DELETE /api/items/{id}

Delete an item.

**Request:**
```http
DELETE /api/items/1
Authorization: Bearer {JWT_TOKEN}
```

**Response (Success):**
```http
HTTP/1.1 204 No Content
```

**Response (Not Found):**
```json
{
  "error": "item_not_found",
  "message": "Item with id 1 not found"
}
```

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {} // Optional additional details
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `validation_error` | 400 | Request validation failed |
| `unauthorized` | 401 | Authentication required |
| `access_denied` | 403 | Insufficient permissions |
| `item_not_found` | 404 | Requested item not found |
| `user_not_found` | 404 | User not found |
| `internal_error` | 500 | Internal server error |

### Authentication Errors

| Code | Description |
|------|-------------|
| `missing_token` | Authorization header missing |
| `invalid_token` | JWT token is invalid or expired |
| `invalid_line_token` | LINE access token is invalid |

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **General endpoints**: 100 requests per minute per IP
- **Authentication endpoints**: 10 requests per minute per IP

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642694400
```

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (starts from 1)
- `page_size`: Number of items per page (max 100)

Pagination information is included in the response:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

## Filtering and Sorting

### Items Filtering

- `search`: Search in name and description
- `min_price`: Minimum price (inclusive)
- `max_price`: Maximum price (inclusive)

### Items Sorting

- `sort_by`: Field to sort by (`name`, `price`, `created_at`)
- `sort_order`: Sort direction (`asc`, `desc`)

## Examples

### Complete Authentication Flow

```bash
# 1. Get LINE OAuth URL (frontend)
LINE_AUTH_URL="https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8000/auth/callback&state=random_state&scope=profile%20openid"

# 2. User authorizes and LINE redirects with access_token

# 3. Exchange LINE token for JWT
curl -X POST http://localhost:8000/auth/line/callback \
  -H "Content-Type: application/json" \
  -d '{"access_token": "LINE_ACCESS_TOKEN"}'

# Response: {"access_token": "JWT_TOKEN", "token_type": "bearer", ...}
```

### CRUD Operations

```bash
# Set JWT token
JWT_TOKEN="your_jwt_token_here"

# Create item
curl -X POST http://localhost:8000/api/items/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MacBook Pro",
    "description": "Apple MacBook Pro 16-inch",
    "price": "2499.99"
  }'

# Get items with filtering
curl -X GET "http://localhost:8000/api/items/?search=macbook&min_price=2000&sort_by=price&sort_order=desc" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Update item
curl -X PUT http://localhost:8000/api/items/1 \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MacBook Pro M3",
    "price": "2299.99"
  }'

# Delete item
curl -X DELETE http://localhost:8000/api/items/1 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Error Handling

```bash
# Invalid token
curl -X GET http://localhost:8000/api/items/ \
  -H "Authorization: Bearer invalid_token"

# Response: {"error": "invalid_token", "message": "Invalid token format"}

# Missing required field
curl -X POST http://localhost:8000/api/items/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Missing name field"}'

# Response: {"error": "validation_error", "message": "Item name is required"}
```

## SDK Examples

### Python

```python
import httpx

class APIClient:
    def __init__(self, base_url: str, jwt_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {jwt_token}"}
    
    async def get_items(self, page: int = 1, search: str = None):
        params = {"page": page}
        if search:
            params["search"] = search
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/items/",
                headers=self.headers,
                params=params
            )
            return response.json()
    
    async def create_item(self, name: str, description: str, price: str):
        data = {
            "name": name,
            "description": description,
            "price": price
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/items/",
                headers=self.headers,
                json=data
            )
            return response.json()

# Usage
client = APIClient("http://localhost:8000", "your_jwt_token")
items = await client.get_items(search="laptop")
new_item = await client.create_item("Gaming PC", "High-end gaming computer", "1999.99")
```

### JavaScript

```javascript
class APIClient {
  constructor(baseUrl, jwtToken) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json'
    };
  }

  async getItems(page = 1, search = null) {
    const params = new URLSearchParams({ page });
    if (search) params.append('search', search);

    const response = await fetch(`${this.baseUrl}/api/items/?${params}`, {
      headers: this.headers
    });
    return response.json();
  }

  async createItem(name, description, price) {
    const response = await fetch(`${this.baseUrl}/api/items/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ name, description, price })
    });
    return response.json();
  }
}

// Usage
const client = new APIClient('http://localhost:8000', 'your_jwt_token');
const items = await client.getItems(1, 'laptop');
const newItem = await client.createItem('Gaming PC', 'High-end gaming computer', '1999.99');
```

## Testing the API

### Using curl

See examples above for curl commands.

### Using Postman

1. Import the API collection (if available)
2. Set up environment variables:
   - `base_url`: http://localhost:8000
   - `jwt_token`: Your JWT token
3. Use the collection to test endpoints

### Using the Interactive Documentation

Visit http://localhost:8000/docs to use the built-in Swagger UI for testing endpoints interactively.