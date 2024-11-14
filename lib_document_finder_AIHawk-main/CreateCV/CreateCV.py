import os
import requests
from langchain import OpenAI
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain_openai import ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

openai_api_key = "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"
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature = 0.8)

import os
from langchain import OpenAI, LLMChain
from langchain.prompts import PromptTemplate

prompt_template = """
Create a detailed resume for a random individual, with random information and personal data (all random). Include the following sections in a random order, and ensure that all data corresponds to the following JSON structure:

{{
  "personal_information": {{
    "name": "<NAME>",
    "surname": "<SURNAME>",
    "date_of_birth": "<DATE_OF_BIRTH>",
    "country": "<COUNTRY>",
    "city": "<CITY>",
    "address": "<ADDRESS>",
    "phone_prefix": "<PHONE_PREFIX>",
    "phone": "<PHONE_NUMBER>",
    "email": "<EMAIL>",
    "github": "<GITHUB_URL>",
    "linkedin": "<LINKEDIN_URL>"
  }},
  "education_details": [
    {{
      "education_level": "<EDUCATION_LEVEL>",
      "institution": "<INSTITUTION>",
      "field_of_study": "<FIELD_OF_STUDY>",
      "final_evaluation_grade": "<FINAL_EVALUATION_GRADE>",
      "start_date": "<START_DATE>",
      "year_of_completion": "<YEAR_OF_COMPLETION>",
      "exam": {{
        "<EXAM_NAME_1>": "<GRADE_1>",
        "<EXAM_NAME_2>": "<GRADE_2>",
        "<EXAM_NAME_3>": "<GRADE_3>",
        "<EXAM_NAME_4>": "<GRADE_4>",
        "<EXAM_NAME_5>": "<GRADE_5>",
        "<EXAM_NAME_6>": "<GRADE_6>"
      }}
    }}
  ],
  "experience_details": [
    {{
      "position": "<POSITION>",
      "company": "<COMPANY>",
      "employment_period": "<EMPLOYMENT_PERIOD>",
      "location": "<LOCATION>",
      "industry": "<INDUSTRY>",
      "key_responsibilities": [
        "<RESPONSIBILITY_1>",
        "<RESPONSIBILITY_2>",
        "<RESPONSIBILITY_3>",
        "<RESPONSIBILITY_4>",
        "<RESPONSIBILITY_5>"
      ],
      "skills_acquired": [
        "<SKILL_1>",
        "<SKILL_2>",
        "<SKILL_3>",
        "<SKILL_4>",
        "<SKILL_5>",
        "<SKILL_6>",
        "<SKILL_7>",
        "<SKILL_8>",
        "<SKILL_9>",
        "<SKILL_10>"
      ]
    }}
  ],
  "projects": [
    {{
      "name": "<PROJECT_NAME_1>",
      "description": "<PROJECT_DESCRIPTION_1>",
      "link": "<PROJECT_LINK_1>"
    }},
    {{
      "name": "<PROJECT_NAME_2>",
      "description": "<PROJECT_DESCRIPTION_2>",
      "link": "<PROJECT_LINK_2>"
    }}
  ],
  "achievements": [
    {{
      "name": "<ACHIEVEMENT_NAME_1>",
      "description": "<ACHIEVEMENT_DESCRIPTION_1>"
    }},
    {{
      "name": "<ACHIEVEMENT_NAME_2>",
      "description": "<ACHIEVEMENT_DESCRIPTION_2>"
    }},
    {{
      "name": "<ACHIEVEMENT_NAME_3>",
      "description": "<ACHIEVEMENT_DESCRIPTION_3>"
    }}
  ],
  "certifications": [
    {{
      "name": "<CERTIFICATION_NAME>",
      "description": "<CERTIFICATION_DESCRIPTION>"
    }}
  ],
  "languages": [
    {{
      "language": "<LANGUAGE_1>",
      "proficiency": "<PROFICIENCY_1>"
    }},
    {{
      "language": "<LANGUAGE_2>",
      "proficiency": "<PROFICIENCY_2>"
    }},
    {{
      "language": "<LANGUAGE_3>",
      "proficiency": "<PROFICIENCY_3>"
    }}
  ],
  "interests": [
    "<INTEREST_1>",
    "<INTEREST_2>",
    "<INTEREST_3>",
    "<INTEREST_4>",
    "<INTEREST_5>",
    "<INTEREST_6>",
    "<INTEREST_7>"
  ],
  "availability": {{
    "notice_period": "<NOTICE_PERIOD>"
  }},
  "salary_expectations": {{
    "salary_range_usd": "<SALARY_RANGE_USD>"
  }},
  "self_identification": {{
    "gender": "<GENDER>",
    "pronouns": "<PRONOUNS>",
    "veteran": "<VETERAN_STATUS>",
    "disability": "<DISABILITY_STATUS>",
    "ethnicity": "<ETHNICITY>"
  }},
  "legal_authorization": {{
    "eu_work_authorization": "<YES/NO>",
    "us_work_authorization": "<YES/NO>",
    "requires_us_visa": "<YES/NO>",
    "requires_us_sponsorship": "<YES/NO>",
    "requires_eu_visa": "<YES/NO>",
    "legally_allowed_to_work_in_eu": "<YES/NO>",
    "legally_allowed_to_work_in_us": "<YES/NO>",
    "requires_eu_sponsorship": "<YES/NO>",
    "canada_work_authorization": "<YES/NO>",
    "requires_canada_visa": "<YES/NO>",
    "legally_allowed_to_work_in_canada": "<YES/NO>",
    "requires_canada_sponsorship": "<YES/NO>",
    "uk_work_authorization": "<YES/NO>",
    "requires_uk_visa": "<YES/NO>",
    "legally_allowed_to_work_in_uk": "<YES/NO>",
    "requires_uk_sponsorship": "<YES/NO>"
  }},
  "work_preferences": {{
    "remote_work": "<YES/NO>",
    "in_person_work": "<YES/NO>",
    "open_to_relocation": "<YES/NO>",
    "willing_to_complete_assessments": "<YES/NO>",
    "willing_to_undergo_drug_tests": "<YES/NO>",
    "willing_to_undergo_background_checks": "<YES/NO>"
  }}
}}

Ensure that the resume is entirely fictional and in Markdown format.

Provide only the markdown code for the resume, without any explanations or additional text and also without ```markdown ```, ```json ```, ``` ```
"""



prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

num_curriculum = 10
curricula = []

for i in range(num_curriculum):
    curriculum = chain.invoke({})
    filename = f"curriculum_{i+1}.json"
    with open(filename, "w", encoding = "utf-8") as file:
        file.write(curriculum)
    curricula.append(curriculum)
    print(f"Creato {filename}")

documents = [Document(page_content=curriculum) for curriculum in curricula]
vectorstore = FAISS.from_documents(documents, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
docs = retriever.invoke("Skill in Python and Machine Learning")

newdoc = ""
for doc in docs:
    newdoc += doc.page_content
    newdoc += "\n\n"
newdoc
prompt = ChatPromptTemplate.from_template("List the key skills from the following resumes:\n{contesto}")
chain_extract = prompt | llm | StrOutputParser()
result = chain_extract.invoke({"contesto": newdoc})
print(result)
prompt_template_query =  """
Given the job description below, and the list of key skills extracted from resumes, identify the most suitable candidate:

Job Description:
{job_description}

Resumes and their key skills:
{resume_skills}

Provide the candidate who matches most closely, along with a detailed explanation of why they are the best fit.
Include a breakdown of how their skills align with the job requirements.
"""

prompt_query = ChatPromptTemplate.from_template(prompt_template_query)
job_description = """
Tech Innovators Inc. is seeking a highly skilled and experienced Senior Data Scientist to join our dynamic team. 
The ideal candidate will have a strong background in data analysis, machine learning, and statistical modeling.
Key skills required include proficiency in Python, experience with deep learning frameworks, cloud platforms, and SQL. 
Strong problem-solving skills and leadership experience are also essential.
"""
job_data = {"job_description": job_description, "resume_skills": result}

chain_query = prompt_query | llm | StrOutputParser()

best_candidate = chain_query.invoke(job_data)

print("Il candidato più adatto è:")
print(best_candidate)
