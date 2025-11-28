# %%
pip install psycopg2-binary

# %%
from pyspark.sql import SparkSession

try:
    spark = SparkSession.getActiveSession()
    if spark:
        spark.stop()
        print("Stopped existing Spark session")
except:
    pass

spark = SparkSession.builder \
    .appName("KafkaToHDFS_And_PostgreSQL_SmartFarming") \
    .config("spark.sql.streaming.kafka.useDeprecatedOffsetFetching", "false") \
    .getOrCreate()

print("✓ New Spark session created")
print(f"Spark version: {spark.version}")

# %%
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType
import psycopg2
import os
import shutil

# Stop all active streaming queries first
spark = SparkSession.getActiveSession()
if spark:
    for query in spark.streams.active:
        print(f"Stopping query: {query.name}")
        query.stop()
    print("All queries stopped")

# Clear checkpoints
checkpoint_paths = [
    "/tmp/checkpoints/kafka_to_hdfs_smartfarming",
    "/tmp/checkpoints/postgres_checkpoint",
    "/tmp/checkpoints/hdfs_checkpoint"
]

for path in checkpoint_paths:
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"Cleared checkpoint: {path}")

# Schema
sensor_schema = StructType() \
    .add("sensor_id", StringType()) \
    .add("timestamp", StringType()) \
    .add("soil_moisture", DoubleType()) \
    .add("soil_pH", DoubleType()) \
    .add("temperature", DoubleType()) \
    .add("rainfall", DoubleType()) \
    .add("humidity", DoubleType()) \
    .add("sunlight_intensity", DoubleType()) \
    .add("pesticide_usage_ml", DoubleType()) \
    .add("farm_id", StringType()) \
    .add("region", StringType()) \
    .add("crop_type", StringType())

spark = SparkSession.builder \
    .appName("KafkaToHDFS_And_PostgreSQL_SmartFarming") \
    .config("spark.sql.streaming.kafka.useDeprecatedOffsetFetching", "false") \
    .getOrCreate()

topic_name = "smart_farming_data"

kafka_bootstrap = "broker:29092"

print(f"Attempting to connect to Kafka at: {kafka_bootstrap}")

# Read from Kafka
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap) \
    .option("subscribe", topic_name) \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("kafka.session.timeout.ms", "30000") \
    .option("kafka.request.timeout.ms", "40000") \
    .option("kafka.default.api.timeout.ms", "60000") \
    .option("maxOffsetsPerTrigger", "1000") \
    .load()

print("Successfully connected to Kafka!")

# Parse JSON
df_parsed = df_raw.selectExpr("CAST(value AS STRING) AS json_str") \
    .withColumn("data", from_json(col("json_str"), sensor_schema)) \
    .select("data.*")

# PostgreSQL writer function
def write_to_postgres(batch_df, epoch_id):
    if batch_df.isEmpty():
        print(f"Batch {epoch_id} is empty")
        return
    
    try:
        conn = psycopg2.connect(
            dbname="smart_farming",
            user="admin", 
            password="password", 
            host="postgres"
        )
        cur = conn.cursor()
        
        rows_written = 0
        for row in batch_df.collect():
            cur.execute("""
                INSERT INTO public.sensor_data (
                    sensor_id, timestamp, soil_moisture, soil_ph, 
                    temperature, rainfall, humidity, sunlight_intensity, 
                    pesticide_usage_ml, farm_id, region, crop_type
                )
                VALUES (%s::uuid, %s::timestamp, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sensor_id) DO NOTHING;
            """, (
                row.sensor_id, 
                row.timestamp, 
                row.soil_moisture, 
                row.soil_pH,
                row.temperature, 
                row.rainfall, 
                row.humidity, 
                row.sunlight_intensity,
                row.pesticide_usage_ml,
                row.farm_id,
                row.region,
                row.crop_type
            ))
            rows_written += 1
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Batch {epoch_id}: {rows_written} records to PostgreSQL")
    except Exception as e:
        print(f"Error batch {epoch_id}: {str(e)}")

# Start streaming to PostgreSQL
postgres_query = df_parsed.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoints/postgres_checkpoint") \
    .trigger(processingTime='10 seconds') \
    .start()

# Start streaming to HDFS
hdfs_output_path = "hdfs://namenode:9000/user/smart_farming_data"

hdfs_query = df_parsed.writeStream \
    .format("parquet") \
    .option("path", hdfs_output_path) \
    .option("checkpointLocation", "/tmp/checkpoints/hdfs_checkpoint") \
    .outputMode("append") \
    .trigger(processingTime='10 seconds') \
    .start()

print("Streaming started:")
print(f"  PostgreSQL: smart_farming.sensor_data")
print(f"  HDFS: {hdfs_output_path}")

# Wait for termination
spark.streams.awaitAnyTermination()


