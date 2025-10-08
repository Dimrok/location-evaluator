import pandas as pd
import numpy as np

# Create realistic French retail store data
stores_data = {
    'store_id': [f'store_{i:02d}' for i in range(1, 10)],
    'name': [f'Pied de Biche {i}' for i in range(1, 10)],
    'city': ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes', 'Strasbourg', 'Montpellier', 'Bordeaux'],
    'latitude': [48.8566, 45.7640, 43.2965, 43.6047, 43.7102, 47.2184, 48.5734, 43.6110, 44.8378],
    'longitude': [2.3522, 4.8357, 5.3698, 1.4442, 7.2620, -1.5536, 7.7521, 3.8767, -0.5792],
    'footfall_daily': np.random.randint(800, 2000, 9),
    'revenue_monthly': np.random.randint(30000, 80000, 9),
    'store_size_sqm': np.random.randint(200, 800, 9),
    'opening_date': pd.date_range('2018-01-01', periods=9, freq='6M').strftime('%Y-%m-%d')
}

stores_df = pd.DataFrame(stores_data)
stores_df.to_csv('data/pied_de_biche_stores.csv', index=False)
print("Sample store data created!")
print(stores_df)

