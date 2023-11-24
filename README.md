# de-projectsv - CBS - inflation
##### Business Problem: 
- NL CBS is open sourced NL statistics, we need to monitor inflation over past few years to get a flavor of its change.
##### Data Source: 
https://opendata.cbs.nl/#/CBS/en/dataset/70936eng/table?searchKeywords=inflation
##### Project phase:
- Testing of fetching data via Odata API service in Postman
- Copying data to Azure container in Azure Data Factory
- ETL in Azure Databricks - bronze - silver - gold stage
- Preparing results for business