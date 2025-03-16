from fastapi import FastAPI, Query
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from pydantic import BaseModel
from datetime import datetime, timezone
from influxdb_client.client.query_api import QueryApi

app = FastAPI()

BUCKET = "station_meteo"
ORG = "ETS"
TOKEN = "K4eUD0ZJssvkFcHmE2-vWnUIN_KeHazimOpfhuSp97ExxkTcDh6D8jDqNgbAEqjHvijWacZGXMxfOtu49Y9YQA=="
URL = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)

class SensorData(BaseModel):
    pluie: int
    temperature_DS18B20: float
    humidite_DHT11: float
    temperature_DHT11: float
    pression_BMP180: float
    temperature_BMP180: float

@app.get("/data")
def get_bucket_data(bucket: str = Query(BUCKET, description="Name of bucket")):
    
    query = f'''
    from(bucket: "{bucket}")
    |> range(start: -1h)  
    |> filter(fn: (r) => r._field == "pluie" or 
                            r._field == "temperature_DS18B20" or 
                            r._field == "humidite_DHT11" or 
                            r._field == "temperature_DHT11" or 
                            r._field == "pression_BMP180" or 
                            r._field == "temperature_BMP180")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"], desc: true) 
    '''

    tables = client.query_api().query(query, org=ORG)

    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time(),
                "pluie": record.values.get("pluie"),
                "temperature_DS18B20": record.values.get("temperature_DS18B20"),
                "humidite_DHT11": record.values.get("humidite_DHT11"),
                "temperature_DHT11": record.values.get("temperature_DHT11"),
                "pression_BMP180": record.values.get("pression_BMP180"),
                "temperature_BMP180": record.values.get("temperature_BMP180"),
            })

    return {"bucket": bucket, "data": results}

@app.post("/add-data")
def add_data(data: SensorData, bucket: str = BUCKET):
    point = influxdb_client.Point("meteo") \
        .field("pluie", data.pluie) \
        .field("temperature_DS18B20", data.temperature_DS18B20) \
        .field("humidite_DHT11", data.humidite_DHT11) \
        .field("temperature_DHT11", data.temperature_DHT11) \
        .field("pression_BMP180", data.pression_BMP180) \
        .field("temperature_BMP180", data.temperature_BMP180)

    client.write_api(write_options=SYNCHRONOUS).write(bucket=bucket, org=ORG, record=point)
    
    return {"message": "Data added with success"}


@app.delete("/delete-data")
def delete_data(bucket: str = Query(BUCKET, description="Name of bucket")):
        start = "1970-01-01T00:00:00Z"
        stop = datetime.now(timezone.utc).isoformat()
        client.delete_api().delete(start, stop, predicate="", bucket=bucket, org=ORG)
        return {"message": f"Data from '{bucket}' where deleted from {start} to {stop}"}