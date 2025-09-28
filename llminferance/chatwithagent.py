from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import re
import datetime
from collections import defaultdict

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "dbname": "agro",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD", "123456"),
    "port": 5432
}

# Initialize LLM
llm = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY", "")
)

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def generate_sql_query(user_query: str) -> str:
    """Generate SQL query from natural language"""
    prompt = f"""You are a SQL generator. Generate a valid PostgreSQL SELECT query.

Table: agrodata
Available columns:
- platform_number (int)
- cycle_number (int) 
- latitude (float)
- longitude (float)
- depth_level (float)
- temperature (float)
- salinity (float)
- dissolved_oxygen (float)
- chlorophyll (float)
- time (timestamp)

Rules:
1. Return ONLY the raw SQL query without ANY explanations or formatting
2. Query MUST start with SELECT
3. Query MUST use the agrodata table
4. NO semicolons at the end
5. NO markdown formatting
6. NO thinking out loud
7. NO explanations

Example valid output:
SELECT temperature, salinity FROM agrodata LIMIT 5

User question: {user_query}"""

    try:
        # Get response from LLM
        response = llm.invoke(prompt)
        sql_query = response.content
        
        # Clean and validate the query
        sql_query = (sql_query
            .replace('```sql', '')
            .replace('```', '')
            .replace('<think>', '')
            .replace('</think>', '')
            .strip()
            .rstrip(';'))
        
        # Force SELECT if missing
        if not sql_query.lower().startswith('select'):
            return "SELECT temperature, salinity FROM agrodata LIMIT 5"
            
        # Force table name if missing
        if 'agrodata' not in sql_query.lower():
            sql_query = sql_query.replace('FROM', 'FROM agrodata')
            
        return sql_query
        
    except Exception as e:
        return "SELECT temperature, salinity FROM agrodata LIMIT 5"

def validate_sql_query(query: str) -> bool:
    """Validate SQL query for security"""
    query_lower = query.lower().strip()
    
    # Must start with SELECT
    if not query_lower.startswith('select'):
        return False
    
    # Check for dangerous keywords
    dangerous_words = ['insert', 'update', 'delete', 'drop', 'truncate', 'alter', 'create']
    if any(word in query_lower for word in dangerous_words):
        return False
    
    # Must contain agrodata table
    if 'agrodata' not in query_lower:
        return False
        
    return True

def execute_query(sql_query: str) -> List[Dict]:
    """Execute SQL query and return results"""
    if not validate_sql_query(sql_query):
        raise ValueError("Invalid or unsafe SQL query")
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Convert datetime to string if needed
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row_dict[col] = value
            result.append(row_dict)
            
        return result
        
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def safe_float(row: Dict, key: str) -> float:
    """Safely convert value to float"""
    try:
        value = row.get(key)
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def format_result(query: str, rows: List[Dict]) -> Dict:
    """Format query results into visualization schema"""
    if not rows:
        return {"type": "empty", "message": "No data found"}

    try:
        query_lower = query.lower()

        # Temperature Profile
        if "temperature" in query_lower and "depth" in query_lower:
            points = [
                {
                    "x": safe_float(row, "temperature"),
                    "y": safe_float(row, "depth_level")
                }
                for row in rows
                if row.get("temperature") is not None 
                and row.get("depth_level") is not None
            ]
            
            if points:
                return {
                    "type": "profile",
                    "x": "temperature",
                    "y": "depth",
                    "invertY": True,
                    "series": [{
                        "name": "Temperature Profile",
                        "points": points
                    }]
                }

        # Salinity Profile
        elif "salinity" in query_lower and "depth" in query_lower:
            return {
                "type": "profile",
                "x": "salinity",
                "y": "depth",
                "invertY": True,
                "series": [{
                    "name": "Salinity Profile",
                    "points": [
                        {
                            "x": row["salinity"],
                            "y": row["depth"]
                        }
                        for row in rows
                        if row.get("salinity") is not None 
                        and row.get("depth") is not None
                    ]
                }]
            }

        # Hovmöller Diagram
        elif "hovmoller" in query_lower or "depth-time" in query_lower:
            return {
                "type": "hovmoller",
                "x": "time",
                "y": "depth",
                "z": "temperature",
                "grid": {
                    "t": [str(row["time"]) for row in rows if row.get("time")],
                    "z": [row["depth"] for row in rows if row.get("depth")],
                    "values": [row["temperature"] for row in rows if row.get("temperature")]
                },
                "contour": True
            }

        # Map View/Trajectories
        elif "map" in query_lower or "trajectory" in query_lower:
            points = [
                {
                    "lon": row["longitude"],
                    "lat": row["latitude"],
                    "time": str(row["time"]) if row.get("time") else None,
                    "floatId": row["platform_number"]
                }
                for row in rows
                if row.get("longitude") is not None 
                and row.get("latitude") is not None
            ]

            # Group points by floatId for paths
            float_paths = defaultdict(list)
            for point in points:
                if point["floatId"]:
                    float_paths[point["FloatId"]].append({
                        "lon": point["lon"],
                        "lat": point["lat"]
                    })

            return {
                "type": "map",
                "points": points,
                "lines": [
                    {
                        "floatId": float_id,
                        "path": path
                    }
                    for float_id, path in float_paths.items()
                ]
            }

        # BGC Time Series
        elif "chlorophyll" in query_lower:
            return {
                "type": "timeseries",
                "metric": "chlorophyll",
                "unit": "mg m^-3",
                "series": [{
                    "name": "Chlorophyll",
                    "points": [
                        {
                            "t": str(row["time"]),
                            "v": row["chlorophyll"]
                        }
                        for row in rows
                        if row.get("time") is not None 
                        and row.get("chlorophyll") is not None
                    ]
                }]
            }

        # Default raw data view
        return {
            "type": "raw",
            "data": rows
        }

    except Exception as e:
        return {
            "type": "error",
            "message": str(e)
        }

def query_database(user_query: str) -> Dict:
    """Main function to query database with formatted response"""
    try:
        # Generate SQL query
        sql_query = generate_sql_query(user_query)
        print(f"Generated SQL: {sql_query}")
        
        # Execute query
        results = execute_query(sql_query)
        
        # Format results based on query type
        formatted_result = format_result(user_query, results)
        
        return {
            "success": True,
            "sql_query": sql_query,
            "count": len(results),
            "result": formatted_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql_query": None,
            "count": 0,
            "result": {
                "type": "error",
                "message": str(e)
            }
        }
