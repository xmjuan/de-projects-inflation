# Databricks notebook source
# MAGIC %md
# MAGIC #### Copy data from CBS using REST API to bronze container in Azure Data Factory

# COMMAND ----------

# MAGIC %md
# MAGIC #### Mounting from data lake to storage account using access key

# COMMAND ----------


# prepare credentials, storage
storage_account_key = "nYA8m8mW7AAi+o6vF5AkfWOMDKhQvDja4eFks4U2k0XhCjPLQ7q/WoLXx3IDHUfzzlIGsBl8SKZh+ASttnzeYw=="
storage_account_name = "testcgssgsegc"
bronze_container = "bronze"
bronze_mountPoint = f"/mnt/testcgssgsegc/{bronze_container}"

silver_container = "silver"
silver_mountPoint = f"/mnt/testcgssgsegc/{silver_container}"

gold_container = "gold"
gold_mountPoint = f"/mnt/testcgssgsegc/{gold_container}"

def mountToDB(storage_account_key, storage_account_name, container, mountPoint):
    # mounting access from data lake to storage for dev
    # if there's a mount point exist, unmount it first
    if any(mount.mountPoint == mountPoint for mount in dbutils.fs.mounts()):
        dbutils.fs.unmount(mountPoint)
    try:
        dbutils.fs.mount(
            source = f"wasbs://{container}@{storage_account_name}.blob.core.windows.net/",
            mount_point = f"{mountPoint}",
            extra_configs = {"fs.azure.account.key." + storage_account_name + ".blob.core.windows.net": storage_account_key}
        )
        print("mount succeeded")
    except Exception as ex:
        print("mount exception", ex)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Create database to contain tables at different stages

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE DATABASE IF NOT EXISTS cbs_inflation;

# COMMAND ----------

# MAGIC %md
# MAGIC #### Bronze Stage

# COMMAND ----------

# mount bronze
mountToDB(storage_account_key, storage_account_name, bronze_container, bronze_mountPoint)

# inspect file
dbutils.fs.ls("/mnt/testcgssgsegc/bronze")

# COMMAND ----------

# read bronze container
sdf_bronze = spark.read.format("json").options(header='true', inferSchema='true').load(f'dbfs:{bronze_mountPoint}')
display(sdf_bronze.limit(5))

# COMMAND ----------

# write as delta table
bronze_table = "cbs_inflation.bronze_inflation"
sdf_bronze.write.format("delta") \
    .mode("overwrite") \
    .option("delta.autooptimize.optimizewrite", "true") \
    .options(inferSchema = 'true') \
    .saveAsTable(bronze_table)

# COMMAND ----------

# MAGIC %sql
# MAGIC ---inspect bronze table using sql
# MAGIC USE cbs_inflation;
# MAGIC SELECT * FROM bronze_inflation LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC #### Silver Stage - data cleaning

# COMMAND ----------

# MAGIC %md
# MAGIC - get rid of AnnualRateOfChangeDerived_2 column
# MAGIC - adjust periods as timeformate
# MAGIC - rename columns

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import DataType

# get rid of AnnualRateOfChangeDerived_2
sdf_silver = spark.sql("SELECT AnnualRateOfChange_1, ID, Periods FROM cbs_inflation.bronze_inflation")

# create YearMonth column from Periods, rename and crop original Periods column
sdf_silver_new = sdf_silver.withColumn("YearMonth", 
                      expr(
                          "TO_DATE(CONCAT(SUBSTR(Periods, 1, 4), '/', SUBSTR(Periods, 7, 2), '/1'), 'yyyy/M/d')")) \
                            .withColumnRenamed("AnnualRateOfChange_1", "AnnualRateOfChange") \
                            .drop("Periods")
display(sdf_silver_new)

# COMMAND ----------

# write into silver table
silver_table = "cbs_inflation.silver_inflation"
sdf_silver_new.write.format("delta") \
    .mode("overwrite") \
    .option("delta.autooptimize.optimizewrite", "true") \
    .options(inferSchema = 'true') \
    .saveAsTable(silver_table)

# ingest into silver layer
sdf_silver_new.write.format("delta") \
    .mode("overwrite") \
    .option("path", silver_mountPoint)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Gold stage - data transformation and aggregation
# MAGIC - aggregate inflation by year

# COMMAND ----------

sdf_gold = spark.sql("SELECT * FROM cbs_inflation.silver_inflation")

sdf_gold_new = sdf_gold.groupBy(year("YearMonth").alias("Year")).agg(avg("AnnualRateOfChange").alias("AvgInflation"))
display(sdf_gold_new)

# COMMAND ----------

# write into golden table
gold_table = "cbs_inflation.gold_inflation"
sdf_gold_new.write.format("delta") \
    .mode("overwrite") \
    .option("delta.autooptimize.optimizewrite", "true") \
    .options(inferSchema = 'true') \
    .saveAsTable(gold_table)

# ingest into silver layer
sdf_gold_new.write.format("delta") \
    .mode("overwrite") \
    .option("path", gold_mountPoint)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Visualization

# COMMAND ----------

# MAGIC %sql
# MAGIC USE cbs_inflation;
# MAGIC SELECT * FROM gold_inflation;

# COMMAND ----------


