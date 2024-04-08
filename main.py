from fastapi import FastAPI, Query, Path, Body, Response
from pydantic import BaseModel
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse
import re
import certifi
ca = certifi.where()

tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users. The **login** logic is also here.",
    }
]
app = FastAPI()


class Address(BaseModel):
    city: str
    country: str

class StudentCreate(BaseModel):
    name: str
    age: int
    address: Address

class StudentId(BaseModel):
    id: str

class StudentResponse(BaseModel):
    name: str
    age: int    

class StudentResponseObj(BaseModel):
    data: list[StudentResponse]  


# Encode username and password
username = 'codeblaster_20'
password = 'India@123'
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

uri = f"mongodb+srv://{encoded_username}:{encoded_password}@pythonapi.vaqhtlv.mongodb.net/?retryWrites=true&w=majority&appName=pythonAPI"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=ca)
db = client['pythonAPI']
collection = db['students']

@app.post("/students", response_model=StudentId, description="API to create a student in the system. All fields are mandatory and required while creating the student in the system.")
async def Create_Students(student_data: StudentCreate):
    total_students = collection.count_documents({})

    next_roll_number = total_students + 1

    student_dict = student_data.dict()
    student_dict['roll_number'] = next_roll_number

    collection.insert_one(student_dict)

    return {"id": str(student_dict['roll_number'])}


@app.get(
        "/students",
        response_model = StudentResponseObj, 
        description="An API to find a list of students. You can apply filters on this API by passing the query parameters as listed below."
    )
async def list_students(
    country: str = Query
    (
        None, 
        description="To apply filter of country. If not given or empty, this filter should be applied."),
        age: int = Query
        (
            None, 
            description="Only records which have age greater than equal to the provided age should be present in the result. If not given or empty, this filter should be applied.", 
            gt=0
        )
    ):
    filter_criteria = {}
    if country:
        country_lower = country.lower()
        filter_criteria["address.country"] = {"$regex": f"^{re.escape(country_lower)}$", "$options": "i"}
    if age is not None:
        filter_criteria["age"] = {"$gte": age}

    cursor = collection.find(filter_criteria)

    result = []
    for doc in cursor:
        result.append({
            "name": doc['name'],
            "age": doc['age']
        })

    return {"data": result}

@app.get("/student/{id}" ,response_model = StudentCreate )
async def fetch_student(id: str = Path(description="The ID of the student previously created")):
    filter_criteria = {}
    filter_criteria['roll_number'] = int(id)

    cur = collection.find_one(filter_criteria)
    result = {}

    result['name'] = cur['name']
    result['age'] = cur['age']
    result['address'] = cur['address']

    return result


@app.patch(
        "/students/{id}",
        status_code=204,
        description="API to update the student's properties based on information provided. Not mandatory that all information would be sent in PATCH, only what fields are sent should be updated in the Database.",
        )
async def update_student(
    id: str, 
    update_data: dict = Body(
        ..., 
        description = "JSON payload containing the updated fields",
        example = {
            "name": "string",
            "age": 0,
            "address": dict({
                "city":"string",
                "country":"string"
                })
            }
        ),
    ):
    id_int = int(id)
    
    filter_criteria = {"roll_number": id_int}
    
    result = collection.update_one(filter_criteria, {"$set": update_data})
    if result.modified_count == 1:
        return {}
    else:
        return {"message": f"Student with ID {id} not found or no changes provided"}

@app.delete("/students/{id}", response_model=dict)
async def delete_student(id : str):
    id_int = int(id)
    filter_criteria = {"roll_number": id_int}
    collection.delete_one(filter_criteria)
    return {}

