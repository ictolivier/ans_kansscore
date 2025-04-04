import requests
import csv
import re
from datetime import datetime
import logging
import json
import pandas as pd
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://ans.uva.nl/api/v2"
SCHOOL_ID = 12
API_TOKEN = "ZET HIER JE API TOKEN NEER"  # Vervang dit door je daadwerkelijke API-token
LIMIT = 100

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}"
}

def rate_limit(response):
    # Check rate limits in headers
    remaining = int(response.headers.get("RateLimit-Remaining", 1))
    school_remaining = int(response.headers.get("RateLimit-School-Remaining", 1))
    reset_time = int(response.headers.get("RateLimit-Reset", 10))  # Default to 10s if missing

    # If approaching the limit, wait before making the next request
    if remaining == 0 or school_remaining == 0:
        logging.warning(f"Rate limit reached. Sleeping for {reset_time} seconds...")
        time.sleep(reset_time)

def get_courses(school_id):
    url = f"{BASE_URL}/schools/{school_id}/courses"
    courses = []
    page = 1
    
    while True:
        try:
            response = requests.get(url, headers=HEADERS, params={'limit': LIMIT, 'page': page})

            if response.status_code == 429:  # Too Many Requests
                reset_time = int(response.headers.get("RateLimit-Reset", 10))  # Default to 10s if missing
                logging.warning(f"Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
                time.sleep(reset_time)
                continue  # Retry the same request

            response.raise_for_status()
            json_response = response.json()
            courses.extend(json_response)
            logging.debug(f"Fetched {len(json_response)} courses from page {page}")

            # If we received fewer than the limit, we are at the last page
            if len(json_response) < 100:
                break

            page += 1  # Move to the next page
            rate_limit(response)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching courses on page {page}: {e}")
            break

    return courses

def get_assignments(course_id):
    url = f"{BASE_URL}/courses/{course_id}/assignments"
    assignments = []
    page = 1

    try:
        while True:
            response = requests.get(url, headers=HEADERS, params={'limit': LIMIT, 'page': page})

            if response.status_code == 429:  # Too Many Requests
                reset_time = int(response.headers.get("RateLimit-Reset", 10))  # Default to 10s if missing
                logging.warning(f"Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
                time.sleep(reset_time)
                continue  # Retry the same request

            response.raise_for_status()
            json_response = response.json()
            assignments.extend(json_response)
            # print(assignments)

            if len(json_response) < 100:
                break  # No more assignments to fetch

            page += 1  # Move to the next page
            rate_limit(response)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching assignments for course {course_id}: {e}")
        return []
    return assignments

def get_exercises(assignment_id):
    url = f"{BASE_URL}/assignments/{assignment_id}/exercises"
    exercises = []
    page = 1

    try:
        while True:
            response = requests.get(url, headers=HEADERS, params={'limit': LIMIT, 'page': page})

            if response.status_code == 429:  # Too Many Requests
                reset_time = int(response.headers.get("RateLimit-Reset", 10))  # Default to 10s if missing
                logging.warning(f"Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
                time.sleep(reset_time)
                continue  # Retry the same request

            response.raise_for_status()
            json_response = response.json()
            if json_response == []:
                exercises.append({"id": 0})
            else:
                exercises.extend(json_response)

            if len(json_response) < 100:
                break  # No more exercises to fetch

            page += 1  # Move to the next page
            rate_limit(response)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching exercises for assignment {assignment_id}: {e}")
        return []
    
    return exercises

def get_exercise_questions(exercise_id):
    url = f"{BASE_URL}/exercises/{exercise_id}/questions"
    questions = []
    page = 1

    try:
        while True:
            response = requests.get(url, headers=HEADERS, params={'limit': LIMIT, 'page': page})

            if response.status_code == 429:  # Too Many Requests
                reset_time = int(response.headers.get("RateLimit-Reset", 10))  # Default to 10s if missing
                logging.warning(f"Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
                time.sleep(reset_time)
                continue  # Retry the same request

            response.raise_for_status()
            json_response = response.json()
            questions.extend(json_response)

            if len(json_response) < 100:
                break  # No more questions to fetch

            page += 1  # Move to the next page
            rate_limit(response)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching exercises for exercise {exercise_id}: {e}")
        return []
    return questions
    
def get_guess_score():
    all_courses = get_courses(school_id=SCHOOL_ID)

    data = {"Course name":[], "Course code":[], "Exam name":[], "Guess correction":[], "Exercise name":[], "Question type":[], "Question points":[], "Question guess score":[]}

    for course in all_courses:
        course_id = course.get('id')
        course_name = course.get('name')
        course_code = course.get('course_code')

        all_assignments = get_assignments(course_id=course_id)

        for assignment in all_assignments:
            assignment_id = assignment.get('id')
            assignment_name = assignment.get('name')
            assignment_guess_correction = assignment.get('grades_settings').get('guess_correction')

            all_exercises = get_exercises(assignment_id=assignment_id)
            for exercise in all_exercises:
                exercise_id = exercise.get('id')
                exercise_name = exercise.get('name')

                if exercise_id == 0: # Don't contiune the loop if the exam is empty (i.e. contains no exercises)
                    break

                all_questions = get_exercise_questions(exercise_id=exercise_id)

                for question in all_questions:
                    # question_id = question.get('id') # Unused
                    question_type = question.get('category')
                    question_points = question.get('points')
                    question_guess_score = question.get('guess_score')

                    data['Course name'].append(course_name)
                    data['Course code'].append(course_code)
                    data['Exam name'].append(assignment_name)
                    data['Guess correction'].append(assignment_guess_correction)
                    data['Exercise name'].append(exercise_name)
                    # data['Question id'].append(question_id)
                    data['Question type'].append(question_type)
                    data['Question points'].append(question_points)
                    data['Question guess score'].append(question_guess_score)

    df = pd.DataFrame.from_dict(data, orient='index')
    df = df.transpose()
    
    print("Number of rows in df: ",len(df.index))

    return df

results = get_guess_score()
results.to_excel("C:\\Users\\ooudebo\\Desktop\\toetsen_v2.xlsx", index=False)
print('--- fin ---')