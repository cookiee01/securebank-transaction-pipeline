#!/usr/bin/env python3
"""
SecureBank Transaction Generator

Generates realistic financial transaction data for testing the SecureBank pipeline.
Includes normal transactions and fraudulent patterns for comprehensive testing.

Usage:
    python transaction_generator.py --count 10000 --fraud-rate 0.02 --output transactions.json
"""

import json
import random
import uuid
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
from faker import Faker
import numpy as np

fake = Faker()

class TransactionGenerator:
    """Generate realistic financial transactions with fraud patterns."""
    
    def __init__(self):
        self.customers = self._load_customers()
        self.merchants = self._load_merchants()
        self.transaction_history = {}  # Track customer transaction patterns
        
    def _load_customers(self) -> List[Dict]:
        """Load or generate customer profiles."""
        # In a real scenario, this would load from a file or database
        customers = []
        for i in range(1000):
            customer = {
                "customer_id": f"cust_{i+1:06d}",
                "age": random.randint(18, 80),
                "income_bracket": random.choice(["20k-40k", "40k-60k", "60k-80k", "80k-100k", "100k+"]),
                "location": {
                    "city": fake.city(),
                    "state": fake.state_abbr(),
                    "country": "US",
                    "latitude": float(fake.latitude()),
                    "longitude": float(fake.longitude())
                },
                "risk_profile": random.choices(
                    ["low", "medium", "high"], 
                    weights=[70, 25, 5]
                )[0],
                "average_monthly_spend": random.uniform(500, 5000),
                "preferred_merchants": random.sample([
                    "grocery", "gas", "restaurant", "online", "retail"
                ], k=random.randint(2, 4)),
                "account_created": fake.date_between(start_date="-5y", end_date="today").isoformat()
            }
            customers.append(customer)
        return customers
    
    def _load_merchants(self) -> List[Dict]:
        """Load or generate merchant profiles."""
        merchant_categories = {
            "grocery": ["Whole Foods", "Safeway", "Kroger", "Joe's Market"],
            "gas": ["Shell", "Exxon", "BP", "Chevron"],
            "restaurant": ["McDonald's", "Starbucks", "Pizza Hut", "Local Cafe"],
            "online": ["Amazon", "eBay", "Online Store", "E-commerce"],
            "retail": ["Target", "Walmart", "Best Buy", "Macy's"],
            "atm": ["Bank ATM", "Credit Union ATM", "Gas Station ATM"]
        }
        
        merchants = []
        for category, names in merchant_categories.items():
            for name in names:
                for i in range(5):  # Multiple locations per merchant
                    merchant = {
                        "merchant_id": f"merch_{category}_{len(merchants)+1:04d}",
                        "name": f"{name} #{i+1}",
                        "category": category,
                        "location": {
                            "city": fake.city(),
                            "state": fake.state_abbr(),
                            "country": "US",
                            "latitude": float(fake.latitude()),
                            "longitude": float(fake.longitude())
                        },
                        "risk_level": random.choices(
                            ["low", "medium", "high"],
                            weights=[80, 15, 5]
                        )[0]
                    }
                    merchants.append(merchant)
        return merchants
    
    def generate_transaction(self, fraud_probability: float = 0.02) -> Dict[str, Any]:
        """Generate a single transaction with optional fraud patterns."""
        customer = random.choice(self.customers)
        customer_id = customer["customer_id"]
        
        # Determine if this should be fraudulent
        is_fraud = random.random() < fraud_probability
        
        if is_fraud:
            return self._generate_fraudulent_transaction(customer)
        else:
            return self._generate_normal_transaction(customer)
    
    def _generate_normal_transaction(self, customer: Dict) -> Dict[str, Any]:
        """Generate a normal transaction based on customer profile."""
        # Select merchant based on customer preferences
        preferred_categories = customer["preferred_merchants"]
        merchant_category = random.choices(
            preferred_categories + ["grocery", "gas", "restaurant"],
            weights=[3] * len(preferred_categories) + [1, 1, 1]
        )[0]
        
        merchant = random.choice([
            m for m in self.merchants if m["category"] == merchant_category
        ])
        
        # Generate amount based on merchant category and customer profile
        base_amount = self._get_typical_amount(merchant_category, customer)
        amount = max(1.0, np.random.normal(base_amount, base_amount * 0.3))
        
        # Generate location (usually near customer's location or merchant)
        location = self._get_transaction_location(customer, merchant, is_fraud=False)
        
        # Generate timestamp (normal business hours preference)
        timestamp = self._get_transaction_timestamp(is_fraud=False)
        
        transaction = {
            "transaction_id": f"txn_{int(timestamp.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": random.choices(
                ["purchase", "withdrawal", "transfer", "deposit"],
                weights=[70, 15, 10, 5]
            )[0],
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": location,
            "timestamp": timestamp.isoformat() + "Z",
            "payment_method": random.choices(
                ["card", "mobile", "bank_transfer", "cash"],
                weights=[60, 25, 10, 5]
            )[0],
            "card_present": random.choice([True, False]),
            "is_fraud": False,
            "risk_score": round(random.uniform(0.0, 0.3), 3),
            "metadata": {
                "source": random.choice(["mobile_app", "web_portal", "atm", "pos"]),
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent()
            }
        }
        
        # Update customer transaction history
        self._update_transaction_history(customer["customer_id"], transaction)
        
        return transaction
    
    def _generate_fraudulent_transaction(self, customer: Dict) -> Dict[str, Any]:
        """Generate a fraudulent transaction with suspicious patterns."""
        fraud_type = random.choices(
            ["velocity", "location", "amount", "time", "merchant"],
            weights=[30, 25, 20, 15, 10]
        )[0]
        
        if fraud_type == "velocity":
            return self._generate_velocity_fraud(customer)
        elif fraud_type == "location":
            return self._generate_location_fraud(customer)
        elif fraud_type == "amount":
            return self._generate_amount_fraud(customer)
        elif fraud_type == "time":
            return self._generate_time_fraud(customer)
        else:
            return self._generate_merchant_fraud(customer)
    
    def _generate_velocity_fraud(self, customer: Dict) -> Dict[str, Any]:
        """Generate rapid-fire transactions (velocity fraud)."""
        merchant = random.choice(self.merchants)
        
        # Multiple transactions in short time
        base_time = datetime.now() - timedelta(minutes=random.randint(1, 30))
        
        amount = random.uniform(50, 500)
        location = customer["location"]  # Same location for velocity fraud
        
        transaction = {
            "transaction_id": f"txn_{int(base_time.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": "purchase",
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": location,
            "timestamp": base_time.isoformat() + "Z",
            "payment_method": "card",
            "card_present": False,
            "is_fraud": True,
            "fraud_type": "velocity",
            "risk_score": round(random.uniform(0.7, 0.9), 3),
            "metadata": {
                "source": "online",
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent(),
                "velocity_indicator": True
            }
        }
        
        return transaction
    
    def _generate_location_fraud(self, customer: Dict) -> Dict[str, Any]:
        """Generate transaction from impossible/unusual location."""
        merchant = random.choice(self.merchants)
        
        # Generate location far from customer's normal location
        fraud_location = {
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "country": random.choice(["CA", "MX", "UK", "FR"])  # International fraud
        }
        
        amount = random.uniform(100, 1000)
        timestamp = datetime.now() - timedelta(minutes=random.randint(30, 180))
        
        transaction = {
            "transaction_id": f"txn_{int(timestamp.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": "purchase",
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": fraud_location,
            "timestamp": timestamp.isoformat() + "Z",
            "payment_method": "card",
            "card_present": False,
            "is_fraud": True,
            "fraud_type": "location",
            "risk_score": round(random.uniform(0.6, 0.85), 3),
            "metadata": {
                "source": "online",
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent(),
                "location_anomaly": True
            }
        }
        
        return transaction
    
    def _generate_amount_fraud(self, customer: Dict) -> Dict[str, Any]:
        """Generate transaction with unusually high amount."""
        merchant = random.choice([
            m for m in self.merchants if m["category"] in ["online", "retail"]
        ])
        
        # Amount much higher than customer's normal spending
        normal_amount = customer["average_monthly_spend"] / 30
        fraud_amount = normal_amount * random.uniform(5, 20)  # 5-20x normal
        
        timestamp = datetime.now() - timedelta(minutes=random.randint(60, 360))
        
        transaction = {
            "transaction_id": f"txn_{int(timestamp.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": "purchase",
            "amount": round(fraud_amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": customer["location"],
            "timestamp": timestamp.isoformat() + "Z",
            "payment_method": "card",
            "card_present": False,
            "is_fraud": True,
            "fraud_type": "amount",
            "risk_score": round(random.uniform(0.75, 0.95), 3),
            "metadata": {
                "source": "online",
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent(),
                "amount_anomaly": True
            }
        }
        
        return transaction
    
    def _generate_time_fraud(self, customer: Dict) -> Dict[str, Any]:
        """Generate transaction at unusual time (late night/early morning)."""
        merchant = random.choice(self.merchants)
        
        # Generate transaction at unusual hours (2-5 AM)
        base_date = fake.date_between(start_date="-30d", end_date="today")
        fraud_hour = random.randint(2, 5)
        timestamp = datetime.combine(base_date, datetime.min.time()) + timedelta(
            hours=fraud_hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        amount = random.uniform(50, 300)
        
        transaction = {
            "transaction_id": f"txn_{int(timestamp.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": "purchase",
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": customer["location"],
            "timestamp": timestamp.isoformat() + "Z",
            "payment_method": "card",
            "card_present": False,
            "is_fraud": True,
            "fraud_type": "time",
            "risk_score": round(random.uniform(0.5, 0.7), 3),
            "metadata": {
                "source": "online",
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent(),
                "time_anomaly": True
            }
        }
        
        return transaction
    
    def _generate_merchant_fraud(self, customer: Dict) -> Dict[str, Any]:
        """Generate transaction at high-risk merchant."""
        # Select high-risk merchant
        high_risk_merchants = [
            m for m in self.merchants if m["risk_level"] == "high"
        ]
        
        if not high_risk_merchants:
            # Fallback to any merchant
            merchant = random.choice(self.merchants)
        else:
            merchant = random.choice(high_risk_merchants)
        
        amount = random.uniform(100, 800)
        timestamp = datetime.now() - timedelta(minutes=random.randint(30, 180))
        
        transaction = {
            "transaction_id": f"txn_{int(timestamp.timestamp())}_{uuid.uuid4().hex[:8]}",
            "customer_id": customer["customer_id"],
            "account_id": f"acc_{customer['customer_id'][5:]}",
            "transaction_type": "purchase",
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "location": merchant["location"],
            "timestamp": timestamp.isoformat() + "Z",
            "payment_method": "card",
            "card_present": False,
            "is_fraud": True,
            "fraud_type": "merchant",
            "risk_score": round(random.uniform(0.6, 0.8), 3),
            "metadata": {
                "source": "pos",
                "device_id": f"device_{uuid.uuid4().hex[:8]}",
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent(),
                "merchant_risk": True
            }
        }
        
        return transaction
    
    def _get_typical_amount(self, merchant_category: str, customer: Dict) -> float:
        """Get typical transaction amount based on merchant category and customer."""
        base_amounts = {
            "grocery": 75,
            "gas": 45,
            "restaurant": 35,
            "online": 120,
            "retail": 85,
            "atm": 100
        }
        
        base = base_amounts.get(merchant_category, 50)
        
        # Adjust based on customer income
        income_multipliers = {
            "20k-40k": 0.7,
            "40k-60k": 0.9,
            "60k-80k": 1.1,
            "80k-100k": 1.3,
            "100k+": 1.6
        }
        
        multiplier = income_multipliers.get(customer["income_bracket"], 1.0)
        return base * multiplier
    
    def _get_transaction_location(self, customer: Dict, merchant: Dict, is_fraud: bool) -> Dict:
        """Get transaction location based on customer and merchant."""
        if is_fraud:
            # For fraud, use random location
            return {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "country": random.choice(["US", "CA", "MX"])
            }
        else:
            # For normal transactions, use merchant location with some variation
            return {
                "latitude": merchant["location"]["latitude"] + random.uniform(-0.1, 0.1),
                "longitude": merchant["location"]["longitude"] + random.uniform(-0.1, 0.1),
                "city": merchant["location"]["city"],
                "state": merchant["location"]["state"],
                "country": merchant["location"]["country"]
            }
    
    def _get_transaction_timestamp(self, is_fraud: bool) -> datetime:
        """Get transaction timestamp with realistic patterns."""
        base_date = fake.date_between(start_date="-7d", end_date="today")
        
        if is_fraud:
            # Fraud can happen at any time
            hour = random.randint(0, 23)
        else:
            # Normal transactions more likely during business hours
            hour = random.choices(
                range(24),
                weights=[1, 1, 1, 1, 1, 1, 2, 4, 6, 8, 10, 12, 
                        12, 10, 8, 6, 8, 10, 12, 8, 6, 4, 3, 2]
            )[0]
        
        return datetime.combine(base_date, datetime.min.time()) + timedelta(
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
    
    def _update_transaction_history(self, customer_id: str, transaction: Dict):
        """Update customer transaction history for pattern tracking."""
        if customer_id not in self.transaction_history:
            self.transaction_history[customer_id] = []
        
        self.transaction_history[customer_id].append({
            "amount": transaction["amount"],
            "timestamp": transaction["timestamp"],
            "merchant_category": transaction["merchant_category"],
            "location": transaction["location"]
        })
        
        # Keep only recent transactions (last 100)
        if len(self.transaction_history[customer_id]) > 100:
            self.transaction_history[customer_id] = self.transaction_history[customer_id][-100:]
    
    def generate_batch(self, count: int, fraud_rate: float = 0.02) -> List[Dict[str, Any]]:
        """Generate a batch of transactions."""
        transactions = []
        
        print(f"Generating {count} transactions with {fraud_rate*100:.1f}% fraud rate...")
        
        for i in range(count):
            if i % 1000 == 0:
                print(f"Generated {i}/{count} transactions...")
            
            transaction = self.generate_transaction(fraud_rate)
            transactions.append(transaction)
        
        fraud_count = sum(1 for t in transactions if t.get("is_fraud", False))
        print(f"Generated {count} transactions ({fraud_count} fraudulent, {count-fraud_count} normal)")
        
        return transactions
    
    def save_to_file(self, transactions: List[Dict], filename: str):
        """Save transactions to JSON file."""
        with open(filename, 'w') as f:
            json.dump(transactions, f, indent=2)
        print(f"Saved {len(transactions)} transactions to {filename}")
    
    def send_to_kinesis(self, transactions: List[Dict], stream_name: str):
        """Send transactions to Kinesis stream."""
        kinesis = boto3.client('kinesis')
        
        print(f"Sending {len(transactions)} transactions to Kinesis stream '{stream_name}'...")
        
        for i, transaction in enumerate(transactions):
            try:
                response = kinesis.put_record(
                    StreamName=stream_name,
                    Data=json.dumps(transaction),
                    PartitionKey=transaction['customer_id']
                )
                
                if i % 100 == 0:
                    print(f"Sent {i}/{len(transactions)} transactions...")
                    
            except Exception as e:
                print(f"Error sending transaction {i}: {e}")
        
        print(f"Successfully sent {len(transactions)} transactions to Kinesis")

def main():
    parser = argparse.ArgumentParser(description="Generate realistic financial transaction data")
    parser.add_argument("--count", type=int, default=1000, help="Number of transactions to generate")
    parser.add_argument("--fraud-rate", type=float, default=0.02, help="Fraud rate (0.0-1.0)")
    parser.add_argument("--output", type=str, default="transactions.json", help="Output file name")
    parser.add_argument("--kinesis", type=str, help="Send to Kinesis stream (stream name)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for Kinesis")
    
    args = parser.parse_args()
    
    # Validate fraud rate
    if not 0.0 <= args.fraud_rate <= 1.0:
        print("Error: Fraud rate must be between 0.0 and 1.0")
        return
    
    # Generate transactions
    generator = TransactionGenerator()
    transactions = generator.generate_batch(args.count, args.fraud_rate)
    
    # Save to file
    generator.save_to_file(transactions, args.output)
    
    # Send to Kinesis if specified
    if args.kinesis:
        generator.send_to_kinesis(transactions, args.kinesis)

if __name__ == "__main__":
    main()
