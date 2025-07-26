"""
SecureBank Transaction Processor Lambda Function

This Lambda function processes financial transactions in real-time:
- Validates transaction data
- Performs fraud detection
- Stores transactions in DynamoDB
- Archives data to S3
- Sends metrics to CloudWatch

Triggered by: Kinesis Data Streams
Environment Variables:
- DYNAMODB_TRANSACTIONS_TABLE: DynamoDB table for transactions
- DYNAMODB_CUSTOMERS_TABLE: DynamoDB table for customer profiles
- S3_RAW_BUCKET: S3 bucket for raw transaction data
- FRAUD_THRESHOLD: Risk score threshold for fraud detection
"""

import json
import boto3
import base64
import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
TRANSACTIONS_TABLE = os.getenv('DYNAMODB_TRANSACTIONS_TABLE', 'SecureBank-Transactions')
CUSTOMERS_TABLE = os.getenv('DYNAMODB_CUSTOMERS_TABLE', 'SecureBank-Customers')
S3_RAW_BUCKET = os.getenv('S3_RAW_BUCKET', 'securebank-transactions-raw')
FRAUD_THRESHOLD = float(os.getenv('FRAUD_THRESHOLD', '0.8'))
VELOCITY_THRESHOLD = int(os.getenv('VELOCITY_THRESHOLD', '5'))
AMOUNT_THRESHOLD_MULTIPLIER = float(os.getenv('AMOUNT_THRESHOLD_MULTIPLIER', '3.0'))

# DynamoDB tables
transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)

class FraudDetector:
    """Fraud detection engine for financial transactions."""
    
    def __init__(self):
        self.risk_weights = {
            'velocity': 0.4,
            'amount': 0.3,
            'location': 0.2,
            'time': 0.1
        }
    
    def calculate_risk_score(self, transaction: Dict, customer_profile: Dict, 
                           recent_transactions: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive fraud risk score."""
        risk_factors = {}
        total_risk = 0.0
        
        # 1. Velocity Risk (multiple transactions in short time)
        velocity_risk = self._check_velocity_risk(transaction, recent_transactions)
        risk_factors['velocity'] = velocity_risk
        total_risk += velocity_risk * self.risk_weights['velocity']
        
        # 2. Amount Risk (unusual transaction amount)
        amount_risk = self._check_amount_risk(transaction, customer_profile)
        risk_factors['amount'] = amount_risk
        total_risk += amount_risk * self.risk_weights['amount']
        
        # 3. Location Risk (transaction from unusual location)
        location_risk = self._check_location_risk(transaction, customer_profile, recent_transactions)
        risk_factors['location'] = location_risk
        total_risk += location_risk * self.risk_weights['location']
        
        # 4. Time Risk (transaction at unusual time)
        time_risk = self._check_time_risk(transaction)
        risk_factors['time'] = time_risk
        total_risk += time_risk * self.risk_weights['time']
        
        # Normalize risk score to 0-1 range
        total_risk = min(max(total_risk, 0.0), 1.0)
        
        return {
            'risk_score': round(total_risk, 3),
            'risk_factors': risk_factors,
            'is_fraud': total_risk > FRAUD_THRESHOLD,
            'fraud_reasons': [factor for factor, score in risk_factors.items() if score > 0.5]
        }
    
    def _check_velocity_risk(self, transaction: Dict, recent_transactions: List[Dict]) -> float:
        """Check for velocity fraud (rapid transactions)."""
        if not recent_transactions:
            return 0.0
        
        # Count transactions in last hour
        current_time = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
        one_hour_ago = current_time - timedelta(hours=1)
        
        recent_count = 0
        for txn in recent_transactions:
            txn_time = datetime.fromisoformat(txn['timestamp'].replace('Z', '+00:00'))
            if txn_time > one_hour_ago:
                recent_count += 1
        
        # Risk increases with number of recent transactions
        if recent_count >= VELOCITY_THRESHOLD:
            return min(1.0, recent_count / (VELOCITY_THRESHOLD * 2))
        
        return 0.0
    
    def _check_amount_risk(self, transaction: Dict, customer_profile: Dict) -> float:
        """Check for amount anomalies."""
        amount = float(transaction['amount'])
        avg_spend = float(customer_profile.get('average_monthly_spend', 1000)) / 30  # Daily average
        
        # High risk for amounts significantly above customer's normal spending
        if amount > avg_spend * AMOUNT_THRESHOLD_MULTIPLIER:
            risk = min(1.0, amount / (avg_spend * AMOUNT_THRESHOLD_MULTIPLIER * 2))
            return risk
        
        # Very high amounts are always risky
        if amount > 10000:
            return 0.8
        
        return 0.0
    
    def _check_location_risk(self, transaction: Dict, customer_profile: Dict, 
                           recent_transactions: List[Dict]) -> float:
        """Check for location anomalies."""
        txn_location = transaction.get('location', {})
        customer_location = customer_profile.get('location', {})
        
        # International transactions from US customers
        if (customer_location.get('country') == 'US' and 
            txn_location.get('country') != 'US'):
            return 0.6
        
        # Check distance from recent transactions
        if recent_transactions and txn_location.get('latitude') and txn_location.get('longitude'):
            for recent_txn in recent_transactions[-5:]:  # Check last 5 transactions
                recent_location = recent_txn.get('location', {})
                if recent_location.get('latitude') and recent_location.get('longitude'):
                    distance = self._calculate_distance(txn_location, recent_location)
                    if distance > 500:  # More than 500 miles
                        return min(0.8, distance / 1000)
        
        return 0.0
    
    def _check_time_risk(self, transaction: Dict) -> float:
        """Check for time-based anomalies."""
        txn_time = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
        hour = txn_time.hour
        
        # Higher risk for transactions between 2 AM and 6 AM
        if 2 <= hour <= 6:
            return 0.4
        
        # Moderate risk for very late/early hours
        if hour < 6 or hour > 22:
            return 0.2
        
        return 0.0
    
    def _calculate_distance(self, loc1: Dict, loc2: Dict) -> float:
        """Calculate distance between two locations (simplified)."""
        try:
            lat1, lon1 = float(loc1['latitude']), float(loc1['longitude'])
            lat2, lon2 = float(loc2['latitude']), float(loc2['longitude'])
            
            # Simplified distance calculation (Haversine formula approximation)
            dlat = abs(lat1 - lat2)
            dlon = abs(lon1 - lon2)
            
            # Very rough approximation: 1 degree ≈ 69 miles
            distance = ((dlat ** 2 + dlon ** 2) ** 0.5) * 69
            return distance
        except (KeyError, ValueError, TypeError):
            return 0.0

class TransactionProcessor:
    """Main transaction processing logic."""
    
    def __init__(self):
        self.fraud_detector = FraudDetector()
    
    def process_transaction(self, transaction_data: Dict) -> Dict[str, Any]:
        """Process a single transaction through the complete pipeline."""
        try:
            # 1. Validate transaction data
            validated_transaction = self._validate_transaction(transaction_data)
            
            # 2. Get customer profile
            customer_profile = self._get_customer_profile(validated_transaction['customer_id'])
            
            # 3. Get recent transaction history
            recent_transactions = self._get_recent_transactions(
                validated_transaction['customer_id'], hours=24
            )
            
            # 4. Perform fraud detection
            fraud_analysis = self.fraud_detector.calculate_risk_score(
                validated_transaction, customer_profile, recent_transactions
            )
            
            # 5. Enrich transaction with fraud analysis
            enriched_transaction = {
                **validated_transaction,
                'risk_score': fraud_analysis['risk_score'],
                'is_fraud': fraud_analysis['is_fraud'],
                'fraud_reasons': fraud_analysis['fraud_reasons'],
                'risk_factors': fraud_analysis['risk_factors'],
                'processed_timestamp': datetime.now().isoformat() + 'Z',
                'processor_version': '1.0.0'
            }
            
            # 6. Store in DynamoDB
            self._store_transaction(enriched_transaction)
            
            # 7. Archive to S3
            self._archive_to_s3(enriched_transaction)
            
            # 8. Update customer profile
            self._update_customer_profile(enriched_transaction, customer_profile)
            
            # 9. Send metrics
            self._send_metrics(enriched_transaction)
            
            # 10. Handle fraud alerts
            if enriched_transaction['is_fraud']:
                self._handle_fraud_alert(enriched_transaction)
            
            logger.info(f"Successfully processed transaction {enriched_transaction['transaction_id']}")
            
            return {
                'status': 'success',
                'transaction_id': enriched_transaction['transaction_id'],
                'risk_score': enriched_transaction['risk_score'],
                'is_fraud': enriched_transaction['is_fraud']
            }
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            raise
    
    def _validate_transaction(self, transaction: Dict) -> Dict[str, Any]:
        """Validate and normalize transaction data."""
        required_fields = [
            'customer_id', 'amount', 'currency', 'merchant_id', 
            'merchant_category', 'timestamp', 'location'
        ]
        
        for field in required_fields:
            if field not in transaction:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate transaction ID if not present
        if 'transaction_id' not in transaction:
            transaction['transaction_id'] = f"txn_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        # Validate amount
        amount = float(transaction['amount'])
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        
        # Validate currency
        if transaction['currency'] not in ['USD', 'EUR', 'GBP', 'CAD']:
            raise ValueError(f"Unsupported currency: {transaction['currency']}")
        
        # Validate location
        location = transaction.get('location', {})
        if not isinstance(location, dict):
            raise ValueError("Location must be an object")
        
        return transaction
    
    def _get_customer_profile(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve customer profile from DynamoDB."""
        try:
            response = customers_table.get_item(Key={'customer_id': customer_id})
            
            if 'Item' not in response:
                # Create basic customer profile if not exists
                profile = {
                    'customer_id': customer_id,
                    'account_created': datetime.now().isoformat() + 'Z',
                    'risk_profile': 'medium',
                    'average_monthly_spend': 1000.0,
                    'transaction_count': 0,
                    'fraud_count': 0
                }
                
                customers_table.put_item(Item=self._convert_to_dynamodb_format(profile))
                return profile
            
            return self._convert_from_dynamodb_format(response['Item'])
            
        except Exception as e:
            logger.error(f"Error retrieving customer profile for {customer_id}: {str(e)}")
            # Return default profile on error
            return {
                'customer_id': customer_id,
                'risk_profile': 'high',  # Conservative default
                'average_monthly_spend': 500.0,
                'transaction_count': 0,
                'fraud_count': 0
            }
    
    def _get_recent_transactions(self, customer_id: str, hours: int = 24) -> List[Dict]:
        """Get recent transactions for a customer."""
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            response = transactions_table.query(
                KeyConditionExpression='customer_id = :customer_id AND #ts >= :start_time',
                ExpressionAttributeNames={
                    '#ts': 'timestamp'
                },
                ExpressionAttributeValues={
                    ':customer_id': customer_id,
                    ':start_time': start_time.isoformat() + 'Z'
                },
                ScanIndexForward=False,  # Most recent first
                Limit=50  # Limit to prevent large scans
            )
            
            return [self._convert_from_dynamodb_format(item) for item in response.get('Items', [])]
            
        except Exception as e:
            logger.error(f"Error retrieving recent transactions for {customer_id}: {str(e)}")
            return []
    
    def _store_transaction(self, transaction: Dict):
        """Store transaction in DynamoDB."""
        try:
            item = self._convert_to_dynamodb_format(transaction)
            transactions_table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"Error storing transaction {transaction['transaction_id']}: {str(e)}")
            raise
    
    def _archive_to_s3(self, transaction: Dict):
        """Archive transaction to S3 data lake."""
        try:
            # Create partition path based on timestamp
            timestamp = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
            partition_path = timestamp.strftime('year=%Y/month=%m/day=%d/hour=%H')
            
            # S3 key
            s3_key = f"transactions/{partition_path}/{transaction['transaction_id']}.json"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=S3_RAW_BUCKET,
                Key=s3_key,
                Body=json.dumps(transaction, default=str),
                ContentType='application/json',
                ServerSideEncryption='aws:kms'
            )
            
        except Exception as e:
            logger.error(f"Error archiving transaction to S3: {str(e)}")
            # Don't raise - S3 archival failure shouldn't stop transaction processing
    
    def _update_customer_profile(self, transaction: Dict, current_profile: Dict):
        """Update customer profile with new transaction data."""
        try:
            # Calculate new averages
            current_count = current_profile.get('transaction_count', 0)
            current_avg = current_profile.get('average_monthly_spend', 0)
            
            # Simple moving average update
            new_count = current_count + 1
            transaction_amount = float(transaction['amount'])
            
            # Update monthly average (simplified calculation)
            if current_count > 0:
                new_avg = ((current_avg * current_count) + transaction_amount) / new_count
            else:
                new_avg = transaction_amount
            
            # Update fraud count
            fraud_count = current_profile.get('fraud_count', 0)
            if transaction['is_fraud']:
                fraud_count += 1
            
            # Update profile
            updated_profile = {
                **current_profile,
                'transaction_count': new_count,
                'average_monthly_spend': round(new_avg, 2),
                'fraud_count': fraud_count,
                'last_transaction_timestamp': transaction['timestamp'],
                'last_updated': datetime.now().isoformat() + 'Z'
            }
            
            customers_table.put_item(Item=self._convert_to_dynamodb_format(updated_profile))
            
        except Exception as e:
            logger.error(f"Error updating customer profile: {str(e)}")
            # Don't raise - profile update failure shouldn't stop transaction processing
    
    def _send_metrics(self, transaction: Dict):
        """Send custom metrics to CloudWatch."""
        try:
            metrics = [
                {
                    'MetricName': 'ProcessedTransactions',
                    'Value': 1,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'TransactionAmount',
                    'Value': float(transaction['amount']),
                    'Unit': 'None'
                },
                {
                    'MetricName': 'RiskScore',
                    'Value': float(transaction['risk_score']),
                    'Unit': 'None'
                }
            ]
            
            if transaction['is_fraud']:
                metrics.append({
                    'MetricName': 'FraudDetected',
                    'Value': 1,
                    'Unit': 'Count'
                })
            
            cloudwatch.put_metric_data(
                Namespace='SecureBank/Transactions',
                MetricData=metrics
            )
            
        except Exception as e:
            logger.error(f"Error sending metrics: {str(e)}")
            # Don't raise - metrics failure shouldn't stop transaction processing
    
    def _handle_fraud_alert(self, transaction: Dict):
        """Handle fraud detection alerts."""
        try:
            # Log fraud detection
            logger.warning(
                f"FRAUD DETECTED: Transaction {transaction['transaction_id']} "
                f"for customer {transaction['customer_id']} "
                f"with risk score {transaction['risk_score']}"
            )
            
            # In a real implementation, this would:
            # - Send SNS notification
            # - Create fraud case in fraud management system
            # - Trigger customer notification
            # - Update fraud prevention rules
            
        except Exception as e:
            logger.error(f"Error handling fraud alert: {str(e)}")
    
    def _convert_to_dynamodb_format(self, item: Dict) -> Dict:
        """Convert Python dict to DynamoDB format."""
        return json.loads(json.dumps(item, default=str), parse_float=Decimal)
    
    def _convert_from_dynamodb_format(self, item: Dict) -> Dict:
        """Convert DynamoDB item to Python dict."""
        return json.loads(json.dumps(item, default=str))

def lambda_handler(event, context):
    """Main Lambda handler for processing Kinesis events."""
    processor = TransactionProcessor()
    
    processed_count = 0
    error_count = 0
    fraud_count = 0
    
    try:
        # Process each record from Kinesis
        for record in event.get('Records', []):
            try:
                # Decode Kinesis data
                payload = json.loads(
                    base64.b64decode(record['kinesis']['data']).decode('utf-8')
                )
                
                # Process transaction
                result = processor.process_transaction(payload)
                
                processed_count += 1
                
                if result.get('is_fraud'):
                    fraud_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing record: {str(e)}")
                continue
        
        # Return summary
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': processed_count,
                'errors': error_count,
                'fraud_detected': fraud_count,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processed': processed_count,
                'errors': error_count,
                'timestamp': datetime.now().isoformat()
            })
        }
