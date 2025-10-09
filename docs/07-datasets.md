# Datasets

## Overview

RIoTBench includes real-world IoT datasets from multiple domains. These datasets provide realistic workloads for benchmarking distributed stream processing systems.

---

## Dataset Catalog

| Dataset | Domain | Sensors | Attributes | Size | Freq | Time Period |
|---------|--------|---------|------------|------|------|-------------|
| **TAXI** | Transportation | ~15,000 taxis | GPS, speed, occupancy | ~1.7M events | 1 min | 7 days |
| **SYS** | Smart City | ~40 stations | Air quality, weather | ~2.3M events | 5 min | 60 days |
| **FIT** | Health/Fitness | Wearables | Accelerometer, HR, temp | ~1M events | 1 sec | Multiple users |
| **CITY** | Urban Infrastructure | Multiple types | Various sensors | ~500K events | Varies | 30 days |
| **GRID** | Smart Grid | ~370 meters | Energy consumption | ~800K events | 15 min | 30 days |

---

## 1. TAXI Dataset

### Description

GPS trajectory data from Beijing taxis, collected as part of the T-Drive project.

### Source

Microsoft T-Drive Project: https://www.microsoft.com/en-us/research/publication/t-drive-driving-directions-based-on-taxi-trajectories/

### Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `taxiId` | String | Unique taxi identifier | "taxi_8345" |
| `timestamp` | Long | Unix timestamp (ms) | 1358102664000 |
| `longitude` | Double | GPS longitude | 116.40739 |
| `latitude` | Double | GPS latitude | 39.90469 |
| `speed` | Double | Speed (km/h) | 45.2 |
| `direction` | Double | Heading (degrees) | 185.0 |
| `occupancy` | Boolean | Passenger present | true |

### Sample Data (CSV)

```csv
taxiId,timestamp,longitude,latitude,speed,direction,occupancy
taxi_8345,1358102664000,116.40739,39.90469,45.2,185.0,true
taxi_8345,1358102724000,116.40756,39.90401,42.8,187.3,true
taxi_3421,1358102664000,116.51233,39.89012,32.1,95.5,false
```

### Sample Data (SenML)

```json
{
  "bn": "urn:taxi:8345",
  "bt": 1358102664,
  "e": [
    {"n": "longitude", "v": 116.40739},
    {"n": "latitude", "v": 39.90469},
    {"n": "speed", "v": 45.2},
    {"n": "direction", "v": 185.0}
  ]
}
```

### Use Cases

- **ETL**: Data cleaning, filtering invalid GPS coordinates
- **STATS**: Traffic flow analysis, speed distribution
- **TRAIN**: Trip duration prediction model training
- **PRED**: Travel time estimation, route recommendation

### Available Models

- `DecisionTreeClassify-TAXI-withVeryGood.model`: Trip quality classification
- `LR-TAXI-Numeric.model`: Travel time prediction
- `TAXI-DTC-1358102664000.model`: Decision tree trained on specific period

### Configuration

```properties
# In tasks_TAXI.properties
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/DecisionTreeClassifyHeaderOnly-TAXI.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/DecisionTreeClassify-TAXI.model
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=3
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=300

PREDICT.LINEAR_REGRESSION.TRAIN.ARFF_PATH=/path/to/linearregressionHeaderOnly-TAXI.arff
PREDICT.LINEAR_REGRESSION.MODEL_PATH=/path/to/LR-TAXI-Numeric.model
PREDICT.LINEAR_REGRESSION.TRAIN.MODEL_UPDATE_FREQUENCY=300
```

---

## 2. SYS (Smart City) Dataset

### Description

Air quality and weather sensor data from ~40 monitoring stations in a smart city deployment.

### Attributes

| Attribute | Type | Description | Range/Unit |
|-----------|------|-------------|------------|
| `timestamp` | Long | Unix timestamp (ms) | - |
| `source` | String | Sensor station ID | "station_01" to "station_40" |
| `temperature` | Double | Temperature | 0.7 - 35.1 °C |
| `humidity` | Double | Relative humidity | 20.3 - 69.1 % |
| `light` | Double | Light intensity | 0 - 5153 lux |
| `dust` | Double | Dust concentration | 83.36 - 3322.67 µg/m³ |
| `airquality_raw` | Integer | Raw air quality index | 12 - 49 |
| `airquality_class` | String | Quality classification | Excellent/Good/Fair/Poor |

### Sample Data (CSV)

```csv
timestamp,source,temperature,humidity,light,dust,airquality_raw
1422748810000,station_12,23.5,45.2,1200,150.5,25
1422748810000,station_07,22.8,48.9,980,165.3,28
1422748870000,station_12,23.6,45.0,1210,148.2,24
```

### Sample Data (SenML)

```json
{
  "bn": "urn:dev:station_12",
  "bt": 1422748810,
  "e": [
    {"n": "temperature", "u": "Cel", "v": 23.5},
    {"n": "humidity", "u": "%RH", "v": 45.2},
    {"n": "light", "u": "lux", "v": 1200},
    {"n": "dust", "u": "ug/m3", "v": 150.5},
    {"n": "airquality", "v": 25}
  ]
}
```

### Use Cases

- **ETL**: Data validation, interpolation of missing values
- **STATS**: Air quality trends, correlation analysis
- **TRAIN**: Air quality classification model training
- **PRED**: Air quality forecasting

### Quality Classification

```
Excellent: airquality_raw <= 15
Good:      15 < airquality_raw <= 25
Fair:      25 < airquality_raw <= 35
Poor:      airquality_raw > 35
```

### Available Models

- `DecisionTreeClassify-SYS.model`: Air quality classification
- `DecisionTreeClassify-SYS-withExcellent.model`: Enhanced classifier
- `LR-SYS-Numeric.model`: Air quality prediction
- `LR-SYS-DecisionTreeNumeric.model`: Hybrid model
- `CITY-DTC-1422748810000.model`: City-specific decision tree
- `CITY-MLR-1422748810000.model`: City-specific linear regression

### Configuration

```properties
# In tasks.properties (default is SYS)
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/DecisionTreeClassifyHeaderOnly-SYS.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/DecisionTreeClassify-SYS.model
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=6

FILTER.RANGE_FILTER.VALID_RANGE=temperature:0.7:35.1,humidity:20.3:69.1,light:0:5153,dust:83.36:3322.67,airquality_raw:12:49

STATISTICS.KALMAN_FILTER.USE_MSG_FIELDLIST=temperature,humidity,light,dust,airquality_raw
```

---

## 3. FIT (Fitness) Dataset

### Description

Wearable sensor data from fitness tracking devices, including accelerometer, heart rate, and temperature sensors.

### Attributes

| Attribute | Type | Description | Unit |
|-----------|------|-------------|------|
| `timestamp` | Long | Unix timestamp (ms) | - |
| `userId` | String | User identifier | "user_001" |
| `accel_x` | Double | X-axis acceleration | m/s² |
| `accel_y` | Double | Y-axis acceleration | m/s² |
| `accel_z` | Double | Z-axis acceleration | m/s² |
| `heart_rate` | Integer | Heart rate | bpm |
| `skin_temp` | Double | Skin temperature | °C |
| `activity` | String | Activity label | Walking/Running/Sitting |

### Sample Data

```csv
timestamp,userId,accel_x,accel_y,accel_z,heart_rate,skin_temp,activity
1417890600200,user_001,0.234,-0.876,9.812,75,32.5,Walking
1417890601200,user_001,0.198,-0.903,9.805,76,32.6,Walking
1417890602200,user_001,1.234,-1.456,9.234,95,33.2,Running
```

### Use Cases

- **ETL**: Activity recognition preprocessing
- **STATS**: Activity duration, calorie estimation
- **TRAIN**: Activity classification model training
- **PRED**: Activity prediction, anomaly detection

### Available Models

- `FIT-DTC-1417890600200.model`: Activity classification
- `bloomfilter-FIT.model`: Valid user filtering

### Configuration Files

```properties
# In tasks_FIT.properties
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/FIT-DTC.model
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter-FIT.model
```

---

## 4. CITY (Urban Infrastructure) Dataset

### Description

Multi-sensor data from urban infrastructure including traffic lights, parking sensors, street lighting.

### Attributes

Varies by sensor type:
- Traffic sensors: vehicle count, average speed
- Parking sensors: occupancy status
- Street lighting: power consumption, operational status
- Weather stations: temperature, precipitation

### Sample Data

```csv
timestamp,sensorType,sensorId,value1,value2,value3,status
1422748810000,traffic,tl_001,45,35.5,0.8,active
1422748810000,parking,pk_015,true,120,0,occupied
1422748810000,lighting,sl_023,85.5,220,1.2,on
```

### Available Models

- `CITY-DTC-1422748810000.model`: City infrastructure classification
- `CITY-MLR-1422748810000.model`: Infrastructure prediction

---

## 5. GRID (Smart Grid) Dataset

### Description

Energy consumption data from smart meters in a residential area.

### Attributes

| Attribute | Type | Description | Unit |
|-----------|------|-------------|------|
| `timestamp` | Long | Reading timestamp | - |
| `meterId` | String | Meter identifier | "meter_001" |
| `voltage` | Double | Line voltage | Volts |
| `current` | Double | Current draw | Amperes |
| `power` | Double | Power consumption | Watts |
| `energy` | Double | Cumulative energy | kWh |
| `powerFactor` | Double | Power factor | 0-1 |

### Sample Data

```csv
timestamp,meterId,voltage,current,power,energy,powerFactor
1422748810000,meter_123,230.5,12.3,2834.15,145.6,0.98
1422748810000,meter_124,229.8,8.7,1999.26,98.3,0.97
```

### Use Cases

- **STATS**: Peak demand analysis, load profiling
- **TRAIN**: Load forecasting model training
- **PRED**: Demand prediction, anomaly detection

---

## Data Format Specifications

### CSV Format

Standard CSV with header row:

```csv
field1,field2,field3,...
value1,value2,value3,...
```

**Requirements**:
- First row: column names
- Comma-separated values
- UTF-8 encoding
- Unix line endings (\n)

### SenML Format

JSON-based sensor markup language:

```json
{
  "bn": "base_name",           // Base name (sensor identifier)
  "bt": 1234567890,            // Base time (Unix timestamp)
  "bu": "unit",                // Base unit
  "e": [                       // Array of measurements
    {
      "n": "measurement_name", // Name
      "u": "unit",             // Unit (optional)
      "v": 123.45,             // Value (numeric)
      "vs": "string_value",    // String value (optional)
      "t": 0                   // Time offset from bt (optional)
    }
  ]
}
```

**SenML Units**:
- Temperature: `Cel` (Celsius)
- Humidity: `%RH` (Relative Humidity)
- Light: `lux`
- Distance: `m` (meters)
- Speed: `m/s`
- Power: `W` (Watts)

---

## Input File Preparation

### Creating Custom Datasets

1. **Prepare CSV File**:

```python
import pandas as pd
import time

# Generate sample data
data = []
for i in range(1000):
    data.append({
        'timestamp': int(time.time() * 1000) + i * 1000,
        'source': f'sensor_{i % 10}',
        'temperature': 20 + (i % 10),
        'humidity': 40 + (i % 20),
        'light': 1000 + (i % 500)
    })

df = pd.DataFrame(data)
df.to_csv('custom_dataset.csv', index=False)
```

2. **Create Schema File**:

```bash
# schema.txt
timestamp
source
temperature
humidity
light
```

3. **Update Configuration**:

```properties
PARSE.CSV_SCHEMA_FILEPATH=/path/to/schema.txt
```

### Converting to SenML

```python
import json

def csv_to_senml(csv_row):
    return {
        "bn": f"urn:sensor:{csv_row['source']}",
        "bt": csv_row['timestamp'] // 1000,
        "e": [
            {"n": "temperature", "u": "Cel", "v": csv_row['temperature']},
            {"n": "humidity", "u": "%RH", "v": csv_row['humidity']},
            {"n": "light", "u": "lux", "v": csv_row['light']}
        ]
    }

# Convert CSV to SenML
with open('data.csv') as f:
    with open('data_senml.csv', 'w') as out:
        for row in csv.DictReader(f):
            out.write(json.dumps(csv_to_senml(row)) + '\n')
```

---

## Scaling Datasets

### Duplicating Events

```bash
# Repeat dataset 10 times
for i in {1..10}; do
    tail -n +2 dataset.csv >> dataset_10x.csv
done
```

### Increasing Event Rate

Modify timestamps to compress time:

```python
import pandas as pd

df = pd.read_csv('dataset.csv')

# Compress time by factor of 10
df['timestamp'] = df['timestamp'] // 10

df.to_csv('dataset_10x_rate.csv', index=False)
```

### Splitting for Multiple Spouts

```bash
# Split into 10 files
split -n l/10 -d dataset.csv dataset_split_

# Add headers to each file
header=$(head -n 1 dataset.csv)
for f in dataset_split_*; do
    sed -i "1i$header" $f
done
```

---

## Dataset Statistics

### SYS Dataset

```
Total Events:     2,360,000
Unique Sensors:   40
Duration:         60 days
Sampling Rate:    5 minutes
Missing Rate:     ~2%
Outliers:         ~0.5%
File Size:        ~180 MB
```

### TAXI Dataset

```
Total Events:     1,700,000
Unique Taxis:     ~15,000
Duration:         7 days
Sampling Rate:    1 minute (per taxi)
Coverage Area:    Beijing metropolitan
File Size:        ~150 MB
```

### FIT Dataset

```
Total Events:     1,000,000
Unique Users:     50
Duration:         Multiple sessions
Sampling Rate:    1 second
Activities:       Walking, Running, Sitting, Standing, Cycling
File Size:        ~85 MB
```

---

## Metadata Files

### City Metadata

```
# city-metadata.txt
station_id,name,latitude,longitude,type
station_01,Downtown North,39.9042,116.4074,urban
station_02,Airport East,40.0801,116.5844,suburban
...
```

### Taxi Metadata

```
# taxi-metadata-fulldataset.txt
taxi_id,registration,model,capacity,license_date
taxi_8345,BJ-A-1234,Toyota Camry,4,2010-03-15
taxi_3421,BJ-B-5678,Hyundai Elantra,4,2012-07-22
...
```

---

## Pre-processing Scripts

### Data Cleaning

```python
import pandas as pd

df = pd.read_csv('raw_data.csv')

# Remove duplicates
df = df.drop_duplicates()

# Handle missing values
df = df.fillna(method='ffill')  # Forward fill

# Remove outliers (3-sigma rule)
for col in ['temperature', 'humidity']:
    mean = df[col].mean()
    std = df[col].std()
    df = df[(df[col] >= mean - 3*std) & (df[col] <= mean + 3*std)]

df.to_csv('clean_data.csv', index=False)
```

### Data Annotation

```python
def classify_air_quality(value):
    if value <= 15: return 'Excellent'
    elif value <= 25: return 'Good'
    elif value <= 35: return 'Fair'
    else: return 'Poor'

df['airquality_class'] = df['airquality_raw'].apply(classify_air_quality)
```

---

## Dataset Citation

When using these datasets in research, please cite:

**TAXI Dataset**:
> Yuan, J., Zheng, Y., Zhang, C., Xie, W., Xie, X., Sun, G., & Huang, Y. (2010). 
> T-drive: driving directions based on taxi trajectories. 
> In Proceedings of the 18th SIGSPATIAL International conference on advances in geographic information systems (pp. 99-108).

**SYS Dataset**:
> Provided as part of RIoTBench benchmark suite.

---

## Next Steps

- Learn how to [Configure](06-configuration.md) benchmarks for your dataset
- Follow [Getting Started](05-getting-started.md) to run benchmarks with these datasets
- Review [Application Benchmarks](03-application-benchmarks.md) to see how datasets are used
