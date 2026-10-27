"""Small-data Spark transformations with shared enforcing Python quality gates.

No Spark imports at module import time. Pinned input bytes are validated on the
bounded driver dataset before Spark aggregation; this is not a big-data design.
"""
from src.azure.contracts import assert_parity


def transform_prepared(spark, prepared):
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructType, StructField, StringType, LongType
    import pandas as pd
    from src.features.build_powerbi_dataset import prepare_powerbi_dataset

    frames = {}
    for name, pdf in prepared.items():
        numeric = {'Medals': ['Rank', 'Gold', 'Silver', 'Bronze', 'Total', 'Rank by Total'],
                   'EntriesGender': ['Female', 'Male', 'Total']}.get(name, [])
        schema = StructType([StructField(c, LongType() if c in numeric else StringType(), True)
                             for c in pdf.columns])
        records = [tuple(None if pd.isna(value) else int(value) if column in numeric else str(value)
                         for column, value in row.items()) for _, row in pdf.iterrows()]
        frames[name] = spark.createDataFrame(records, schema)
    a = frames['Athletes'].groupBy('Country').agg(
        F.countDistinct('PersonName').alias('athlete_count'),
        F.countDistinct('Discipline').alias('athlete_discipline_count'))
    t = frames['Teams'].dropDuplicates(['Country', 'Discipline', 'Event', 'TeamName'])
    counts = t.groupBy('Country').agg(F.count('*').alias('team_count'),
        F.countDistinct('Discipline').alias('team_discipline_count'),
        F.countDistinct(F.struct('Discipline', 'Event')).alias('team_event_count'))
    medals = frames['Medals'].select(F.col('TeamCountry').alias('Country'), 'Gold', 'Silver', 'Bronze', 'Total')
    columns = ['country', 'athlete_count', 'athlete_discipline_count', 'team_count',
               'team_discipline_count', 'team_event_count', 'Gold', 'Silver', 'Bronze', 'Total']
    features = a.join(counts, 'Country', 'full').join(medals, 'Country', 'left').fillna(0).withColumnRenamed(
        'Country', 'country').select(columns)
    analytics = features.withColumn('medal_rate_per_athlete', F.when(F.col('athlete_count') != 0,
        F.col('Total') / F.col('athlete_count')).otherwise(F.lit(0.0))).withColumn('gold_share',
        F.when(F.col('Total') != 0, F.col('Gold') / F.col('Total')).otherwise(F.lit(0.0))).withColumn(
        'medals_per_discipline', F.when(F.col('athlete_discipline_count') != 0,
        F.col('Total') / F.col('athlete_discipline_count')).otherwise(F.lit(0.0))).withColumn(
        'performance_class', F.when(F.col('Total') == 0, F.lit('No Medal')).when(
            F.col('Total') <= 9, F.lit('Medal')).otherwise(F.lit('High Medal')))
    # Only these small country-level exports use pandas. No ML training occurs.
    outputs = {'country_features.csv': features.orderBy('country').toPandas(),
               'country_analytics.csv': analytics.orderBy('country').toPandas()}
    outputs['olympic_country_dashboard.csv'] = prepare_powerbi_dataset(outputs['country_analytics.csv'])
    return frames, outputs


def verify_reference_parity(outputs, reference_bytes):
    import io
    import pandas as pd
    for name, output in outputs.items():
        assert_parity(output, pd.read_csv(io.BytesIO(reference_bytes[name])))
