# SecureBank API Reference

## 🌐 API Overview

The SecureBank Transaction API provides secure endpoints for processing financial transactions, retrieving transaction history, and accessing fraud detection insights.

**Base URL**: `https://api.securebank.example.com/v1`  
**Authentication**: AWS IAM + API Keys  
**Rate Limiting**: 1,000 requests per minute per API key  
**Data Format**: JSON  

## 🔐 Authentication

### API Key Authentication
```http
GET /v1/transactions HTTP/1.1
Host: api.securebank.example.com
X-API-Key: your-api-key-here
Content-Type: application/json
```

### AWS IAM Authentication (Advanced)
```http
POST /v1/transactions HTTP/1.1
Host: api.securebank.example.com
Authorization: AWS4-HMAC-SHA256 Credential=...
Content-Type: application/json
```

## 📋 API Endpoints

### 1. Submit Transaction

Submit a new financial transaction for processing.

```http
POST /v1/transactions
```

#### Request Body
```json
{
  "customer_id": "cust_123456",
  "account_id": "acc_789012",
  "transaction_type": "purchase",
  "amount": 150.75,
  "currency": "USD",
  "merchant_id": "merch_456789",
  "merchant_category": "grocery",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "city": "New York",
    "state": "NY",
    "country": "US"
  },
  "payment_method": "card",
  "card_present": true,
  "metadata": {
    "source": "mobile_app",
    "app_version": "2.1.0"
  }
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_id` | string | ✅ | Unique customer identifier |
| `account_id` | string | ✅ | Customer account identifier |
| `transaction_type` | string | ✅ | Type: `purchase`, `withdrawal`, `transfer`, `deposit` |
| `amount` | number | ✅ | Transaction amount (positive decimal) |
| `currency` | string | ✅ | ISO 4217 currency code (e.g., "USD") |
| `merchant_id` | string | ✅ | Unique merchant identifier |
| `merchant_category` | string | ✅ | Category: `grocery`, `gas`, `restaurant`, `online`, `atm` |
| `location` | object | ✅ | Transaction location details |
| `location.latitude` | number | ✅ | Latitude (-90 to 90) |
| `location.longitude` | number | ✅ | Longitude (-180 to 180) |
| `location.city` | string | ❌ | City name |
| `location.state` | string | ❌ | State/province code |
| `location.country` | string | ✅ | ISO 3166-1 alpha-2 country code |
| `payment_method` | string | ✅ | Method: `card`, `mobile`, `bank_transfer` |
| `card_present` | boolean | ❌ | Whether card was physically present |
| `metadata` | object | ❌ | Additional transaction metadata |

#### Success Response (201 Created)
```json
{
  "transaction_id": "txn_1642534567890_abc123",
  "status": "approved",
  "risk_score": 0.15,
  "is_fraud": false,
  "processed_at": "2024-01-18T14:30:45.123Z",
  "processor_response": "approved",
  "authorization_code": "AUTH123456",
  "fees": {
    "processing_fee": 0.30,
    "currency": "USD"
  }
}
```

#### Error Response (400 Bad Request)
```json
{
  "error": {
    "code": "INVALID_AMOUNT",
    "message": "Transaction amount must be greater than 0",
    "details": {
      "field": "amount",
      "provided_value": -10.50
    }
  },
  "timestamp": "2024-01-18T14:30:45.123Z",
  "request_id": "req_abc123def456"
}
```

#### Fraud Detection Response (202 Accepted)
```json
{
  "transaction_id": "txn_1642534567890_xyz789",
  "status": "pending_review",
  "risk_score": 0.85,
  "is_fraud": true,
  "fraud_reasons": [
    "velocity_anomaly",
    "location_anomaly",
    "amount_anomaly"
  ],
  "processed_at": "2024-01-18T14:30:45.123Z",
  "review_required": true,
  "estimated_review_time": "15 minutes"
}
```

### 2. Get Transaction Details

Retrieve details for a specific transaction.

```http
GET /v1/transactions/{transaction_id}
```

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|--------------|
| `transaction_id` | string | Unique transaction identifier |

#### Success Response (200 OK)
```json
{
  "transaction_id": "txn_1642534567890_abc123",
  "customer_id": "cust_123456",
  "account_id": "acc_789012",
  "transaction_type": "purchase",
  "amount": 150.75,
  "currency": "USD",
  "merchant": {
    "merchant_id": "merch_456789",
    "name": "Joe's Grocery Store",
    "category": "grocery",
    "location": {
      "city": "New York",
      "state": "NY",
      "country": "US"
    }
  },
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "city": "New York",
    "state": "NY",
    "country": "US"
  },
  "timestamp": "2024-01-18T14:30:45.123Z",
  "processed_at": "2024-01-18T14:30:45.456Z",
  "status": "approved",
  "risk_assessment": {
    "risk_score": 0.15,
    "is_fraud": false,
    "fraud_indicators": [],
    "model_version": "v2.1.0"
  },
  "payment_details": {
    "payment_method": "card",
    "card_present": true,
    "authorization_code": "AUTH123456",
    "processor_response": "approved"
  },
  "fees": {
    "processing_fee": 0.30,
    "currency": "USD"
  }
}
```

### 3. Get Customer Transaction History

Retrieve transaction history for a specific customer.

```http
GET /v1/customers/{customer_id}/transactions
```

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|--------------|
| `customer_id` | string | Unique customer identifier |

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Number of transactions to return (1-100) |
| `start_date` | string | 30 days ago | Start date (ISO 8601 format) |
| `end_date` | string | now | End date (ISO 8601 format) |
| `transaction_type` | string | all | Filter by transaction type |
| `merchant_category` | string | all | Filter by merchant category |
| `status` | string | all | Filter by status: `approved`, `declined`, `pending` |
| `include_fraud` | boolean | true | Include flagged fraud transactions |

#### Example Request
```http
GET /v1/customers/cust_123456/transactions?limit=50&start_date=2024-01-01&merchant_category=grocery
```

#### Success Response (200 OK)
```json
{
  "customer_id": "cust_123456",
  "transactions": [
    {
      "transaction_id": "txn_1642534567890_abc123",
      "amount": 150.75,
      "currency": "USD",
      "merchant_name": "Joe's Grocery Store",
      "merchant_category": "grocery",
      "timestamp": "2024-01-18T14:30:45.123Z",
      "status": "approved",
      "risk_score": 0.15
    },
    {
      "transaction_id": "txn_1642534567890_def456",
      "amount": 45.20,
      "currency": "USD",
      "merchant_name": "Coffee Shop",
      "merchant_category": "restaurant",
      "timestamp": "2024-01-18T08:15:30.789Z",
      "status": "approved",
      "risk_score": 0.05
    }
  ],
  "pagination": {
    "total_count": 247,
    "returned_count": 2,
    "has_more": true,
    "next_cursor": "eyJsYXN0X2V2YWx1YXRlZF9rZXkiOiB7InRyYW5zYWN0aW9uX2lkIjogInR4bl8xNjQyNTM0NTY3ODkwX2RlZjQ1NiJ9fQ=="
  },
  "summary": {
    "total_amount": 12450.75,
    "transaction_count": 247,
    "average_amount": 50.41,
    "fraud_count": 2
  }
}
```

### 4. Fraud Detection Insights

Get fraud detection insights and patterns.

```http
GET /v1/fraud/insights
```

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_range` | string | 7d | Time range: `1d`, `7d`, `30d`, `90d` |
| `customer_id` | string | - | Filter by specific customer |
| `risk_threshold` | number | 0.5 | Minimum risk score to include |

#### Success Response (200 OK)
```json
{
  "period": {
    "start_date": "2024-01-11T00:00:00Z",
    "end_date": "2024-01-18T23:59:59Z",
    "duration_days": 7
  },
  "fraud_statistics": {
    "total_transactions": 45672,
    "fraud_detected": 234,
    "fraud_rate": 0.0051,
    "false_positive_rate": 0.0023,
    "amount_saved": 45670.25
  },
  "top_fraud_patterns": [
    {
      "pattern": "velocity_anomaly",
      "count": 87,
      "description": "Multiple transactions in short time period",
      "avg_risk_score": 0.78
    },
    {
      "pattern": "location_anomaly",
      "count": 65,
      "description": "Transactions from unusual geographic locations",
      "avg_risk_score": 0.82
    },
    {
      "pattern": "amount_anomaly",
      "count": 52,
      "description": "Transaction amounts significantly above normal",
      "avg_risk_score": 0.73
    }
  ],
  "merchant_risk_analysis": [
    {
      "merchant_category": "online",
      "fraud_rate": 0.0089,
      "risk_level": "high"
    },
    {
      "merchant_category": "atm",
      "fraud_rate": 0.0034,
      "risk_level": "medium"
    }
  ]
}
```

### 5. Health Check

Check API service health and status.

```http
GET /v1/health
```

#### Success Response (200 OK)
```json
{
  "status": "healthy",
  "timestamp": "2024-01-18T14:30:45.123Z",
  "version": "1.2.0",
  "services": {
    "api_gateway": "healthy",
    "lambda_processor": "healthy",
    "dynamodb": "healthy",
    "kinesis": "healthy",
    "fraud_detector": "healthy"
  },
  "metrics": {
    "requests_per_minute": 1247,
    "avg_response_time_ms": 45,
    "error_rate": 0.001
  }
}
```

## 📊 Response Codes

| Code | Status | Description |
|------|--------|--------------|
| 200 | OK | Request successful |
| 201 | Created | Transaction created successfully |
| 202 | Accepted | Transaction pending fraud review |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## 🚨 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
      "field": "specific_field_name",
      "provided_value": "invalid_value",
      "expected_format": "expected_format_description"
    }
  },
  "timestamp": "2024-01-18T14:30:45.123Z",
  "request_id": "req_abc123def456"
}
```

### Common Error Codes

| Error Code | Description | Status Code |
|------------|-------------|-------------|
| `INVALID_AMOUNT` | Transaction amount is invalid | 400 |
| `INVALID_CURRENCY` | Currency code not supported | 400 |
| `INVALID_LOCATION` | Location coordinates are invalid | 400 |
| `CUSTOMER_NOT_FOUND` | Customer ID does not exist | 404 |
| `MERCHANT_NOT_FOUND` | Merchant ID does not exist | 404 |
| `TRANSACTION_NOT_FOUND` | Transaction ID does not exist | 404 |
| `DUPLICATE_TRANSACTION` | Transaction already exists | 409 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INSUFFICIENT_FUNDS` | Account has insufficient balance | 402 |
| `BLOCKED_TRANSACTION` | Transaction blocked by fraud rules | 403 |

## 🔒 Security Considerations

### Request Validation
- All amounts must be positive decimal numbers
- Currency codes must be valid ISO 4217 codes
- Location coordinates must be within valid ranges
- Customer and merchant IDs must exist in the system

### Rate Limiting
- 1,000 requests per minute per API key
- Burst limit of 100 requests per second
- Rate limits apply per endpoint
- Exceeded limits return 429 status code

### Data Privacy
- PII is encrypted in transit and at rest
- Customer data is anonymized in logs
- Compliance with PCI DSS requirements
- GDPR data protection standards

## 📝 SDK Examples

### Python SDK
```python
import requests
import json

# Configuration
API_BASE_URL = "https://api.securebank.example.com/v1"
API_KEY = "your-api-key-here"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Submit transaction
transaction_data = {
    "customer_id": "cust_123456",
    "account_id": "acc_789012",
    "transaction_type": "purchase",
    "amount": 150.75,
    "currency": "USD",
    "merchant_id": "merch_456789",
    "merchant_category": "grocery",
    "location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "country": "US"
    },
    "payment_method": "card"
}

response = requests.post(
    f"{API_BASE_URL}/transactions",
    headers=headers,
    json=transaction_data
)

if response.status_code == 201:
    result = response.json()
    print(f"Transaction approved: {result['transaction_id']}")
elif response.status_code == 202:
    result = response.json()
    print(f"Transaction pending review: {result['transaction_id']}")
else:
    error = response.json()
    print(f"Error: {error['error']['message']}")
```

### cURL Examples
```bash
# Submit transaction
curl -X POST https://api.securebank.example.com/v1/transactions \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123456",
    "account_id": "acc_789012",
    "transaction_type": "purchase",
    "amount": 150.75,
    "currency": "USD",
    "merchant_id": "merch_456789",
    "merchant_category": "grocery",
    "location": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "country": "US"
    },
    "payment_method": "card"
  }'

# Get transaction details
curl -X GET https://api.securebank.example.com/v1/transactions/txn_1642534567890_abc123 \
  -H "X-API-Key: your-api-key-here"

# Get customer transaction history
curl -X GET "https://api.securebank.example.com/v1/customers/cust_123456/transactions?limit=20&merchant_category=grocery" \
  -H "X-API-Key: your-api-key-here"
```

## 🧪 Testing

### Postman Collection
A complete Postman collection is available at `/src/api/postman-collection.json` with:
- All API endpoints
- Example requests and responses
- Environment variables
- Automated tests

### Test Data
Use these test customer IDs for development:
- `cust_test_001` - Normal spending patterns
- `cust_test_002` - High-risk profile
- `cust_test_003` - International transactions
- `cust_fraud_001` - Triggers fraud detection

### Sandbox Environment
**Base URL**: `https://api-sandbox.securebank.example.com/v1`  
**Features**: 
- No rate limiting
- Simulated fraud scenarios
- Test payment processing
- Mock merchant data

---

For additional support or questions about the API, please refer to the [GitHub Issues](https://github.com/cookiee01/securebank-transaction-pipeline/issues) or contact the development team.