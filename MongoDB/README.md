## MongoDB
### Installation:
1. Head to MongoDB directory
```
cd MongoDB
```
2. Launch docker-compose
```
docker-compose up -d
```
3. Activate venv
```
source venv/bin/activate
```
4. Install requirements
```
pip install -r requirements.txt
```
5. Run the migration script to fill up the database
```
python3 migrate.py
```
6. Visit http://localhost:8081/ to confirm everything works