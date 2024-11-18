import os
import psycopg
from openai import OpenAI
from pgvector.psycopg import register_vector

# Step 1: Set up OpenAI API Key
openai_api_key = "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"
os.environ["OPENAI_API_KEY"] = openai_api_key

# Step 2: Initialize OpenAI client
client = OpenAI()



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
import random

# Replace with your actual OpenAI API key
openai_api_key = "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"
llm = ChatOpenAI(api_key=openai_api_key,model_name="gpt-4o-mini", temperature = 0.8)

# Define skills associated with each industry
industry_skills = {
    "Technology": {
        "Programming Languages": [
            "Python", "Java", "C++", "JavaScript", "Ruby", "PHP", "Swift", "Go",
            "Kotlin", "Rust", "Perl", "Scala", "Haskell", "Elixir", "C#",
            "Objective-C", "Matlab", "R", "Dart", "TypeScript"
        ],
        "Frameworks": [
            "React", "Angular", "Django", "Flask", "Laravel", "Ruby on Rails",
            "Spring", "Vue.js", "Node.js", "Express", "Meteor", "Ember.js",
            "Backbone.js", "Symfony", "Zend", "ASP.NET", "TensorFlow", "PyTorch",
            "Keras", "FastAPI"
        ],
        "Tools": [
            "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Jenkins",
            "Jira", "Slack", "Trello", "Ansible", "Chef", "Puppet", "Vagrant",
            "Visual Studio Code", "Eclipse", "IntelliJ IDEA", "Postman", "Figma",
            "Adobe Photoshop"
        ],
        "Soft Skills": [
            "Problem-solving", "Critical Thinking", "Teamwork", "Communication",
            "Adaptability"
        ],
    },
    "Finance": {
        "Skills": [
            "Financial Analysis", "Budgeting", "Accounting", "Forecasting",
            "Risk Management", "Financial Modeling", "Investment Strategies",
            "Tax Planning", "Auditing", "Regulatory Compliance", "Corporate Finance",
            "Mergers and Acquisitions"
        ],
        "Tools": [
            "Excel", "QuickBooks", "SAP", "Oracle Financials", "Hyperion",
            "Bloomberg Terminal", "SQL", "Python", "R", "SAS", "Tableau", "Power BI"
        ],
        "Soft Skills": [
            "Attention to Detail", "Analytical Thinking", "Ethical Judgment",
            "Problem-solving", "Time Management", "Communication", "Decision Making"
        ],
    },
    "Healthcare": {
        "Skills": [
            "Patient Care", "Medical Terminology", "EMR Systems", "Pharmacology",
            "Healthcare Management", "Clinical Research", "Medical Coding",
            "Public Health", "Anatomy", "Physiology", "Diagnostic Skills",
            "Therapeutic Skills"
        ],
        "Certifications": [
            "BLS", "ACLS", "PALS", "Certified Nursing Assistant", "Registered Nurse",
            "CPR Certification", "Medical License", "First Aid"
        ],
        "Soft Skills": [
            "Compassion", "Attention to Detail", "Communication", "Teamwork",
            "Stress Management", "Empathy", "Adaptability"
        ],
    },
    "Construction": {
        "Skills": [
            "Carpentry", "Masonry", "Plumbing", "Electrical Work", "Welding",
            "Painting", "Roofing", "Blueprint Reading", "Heavy Machinery Operation",
            "Safety Compliance", "Project Management", "Cost Estimation"
        ],
        "Tools": [
            "Power Tools", "Hand Tools", "Surveying Equipment", "Cranes",
            "Forklifts", "Excavators", "Concrete Mixers", "Safety Harnesses"
        ],
        "Soft Skills": [
            "Physical Stamina", "Attention to Detail", "Teamwork",
            "Problem-solving", "Time Management", "Leadership", "Communication"
        ],
    },
    "Education": {
        "Skills": [
            "Curriculum Development", "Lesson Planning", "Classroom Management",
            "Assessment Design", "Educational Technology", "Special Education",
            "ESL Instruction", "Subject Matter Expertise"
        ],
        "Certifications": [
            "Teaching Credential", "TESOL Certification", "Special Education Endorsement"
        ],
        "Soft Skills": [
            "Communication", "Patience", "Creativity", "Adaptability",
            "Organization", "Empathy"
        ],
    },
    "Retail": {
        "Skills": [
            "Customer Service", "Sales Techniques", "Inventory Management",
            "Point of Sale Systems", "Visual Merchandising", "Product Knowledge",
            "Cash Handling", "Loss Prevention"
        ],
        "Tools": [
            "POS Systems", "Inventory Software", "CRM Software", "Microsoft Office"
        ],
        "Soft Skills": [
            "Communication", "Teamwork", "Problem-solving", "Time Management",
            "Adaptability", "Attention to Detail"
        ],
    },
    "Manufacturing": {
        "Skills": [
            "Quality Control", "Assembly Line Work", "Machine Operation",
            "Lean Manufacturing", "Six Sigma", "CNC Machining", "Welding",
            "Maintenance", "Safety Protocols"
        ],
        "Tools": [
            "CNC Machines", "CAD Software", "PLC Programming", "Robotics",
            "Hand Tools", "Power Tools"
        ],
        "Soft Skills": [
            "Attention to Detail", "Teamwork", "Problem-solving", "Time Management",
            "Physical Stamina", "Adaptability"
        ],
    },
    "Media": {
        "Skills": [
            "Content Creation", "Video Editing", "Photography", "Graphic Design",
            "Social Media Management", "Copywriting", "SEO", "Journalism",
            "Public Relations"
        ],
        "Tools": [
            "Adobe Creative Suite", "Final Cut Pro", "WordPress", "Google Analytics",
            "Social Media Platforms", "SEO Tools"
        ],
        "Soft Skills": [
            "Creativity", "Communication", "Time Management", "Attention to Detail",
            "Teamwork", "Adaptability"
        ],
    },
    "Energy": {
        "Skills": [
            "Electrical Engineering", "Renewable Energy Systems", "Petroleum Engineering",
            "Energy Management", "Power Generation", "Environmental Compliance",
            "Project Management", "Safety Protocols"
        ],
        "Tools": [
            "SCADA Systems", "AutoCAD", "MATLAB", "GIS Software", "Power Tools"
        ],
        "Soft Skills": [
            "Analytical Thinking", "Problem-solving", "Teamwork", "Communication",
            "Attention to Detail"
        ],
    },
    "Transportation": {
        "Skills": [
            "Logistics", "Fleet Management", "Route Planning", "Vehicle Maintenance",
            "Supply Chain Management", "Dispatching", "Customer Service"
        ],
        "Tools": [
            "GPS Systems", "Logistics Software", "Fleet Tracking Tools",
            "Microsoft Office"
        ],
        "Soft Skills": [
            "Time Management", "Communication", "Problem-solving", "Attention to Detail",
            "Teamwork"
        ],
    },
    "Hospitality": {
        "Skills": [
            "Customer Service", "Event Planning", "Hotel Management", "Culinary Skills",
            "Housekeeping", "Front Desk Operations", "Reservation Systems",
            "Food and Beverage Service"
        ],
        "Tools": [
            "POS Systems", "Reservation Software", "Microsoft Office", "Inventory Software"
        ],
        "Soft Skills": [
            "Communication", "Teamwork", "Problem-solving", "Adaptability",
            "Attention to Detail", "Time Management"
        ],
    },
    "Agriculture": {
        "Skills": [
            "Crop Management", "Animal Husbandry", "Farm Equipment Operation",
            "Soil Science", "Irrigation Systems", "Organic Farming", "Agronomy",
            "Pest Control"
        ],
        "Tools": [
            "Tractors", "Harvesters", "Irrigation Systems", "GPS Technology",
            "Drones"
        ],
        "Soft Skills": [
            "Physical Stamina", "Attention to Detail", "Problem-solving",
            "Time Management", "Teamwork"
        ],
    },
    "Automotive": {
        "Skills": [
            "Vehicle Maintenance", "Mechanical Diagnostics", "Engine Repair",
            "Electrical Systems", "Brake Systems", "Transmission Repair",
            "Customer Service", "Safety Compliance"
        ],
        "Tools": [
            "Diagnostic Tools", "Hand Tools", "Power Tools", "Lifts", "Welding Equipment"
        ],
        "Soft Skills": [
            "Attention to Detail", "Problem-solving", "Time Management",
            "Communication", "Teamwork"
        ],
    },
    "Entertainment": {
        "Skills": [
            "Acting", "Directing", "Scriptwriting", "Music Production", "Choreography",
            "Stage Management", "Sound Engineering", "Lighting Design", "Set Design"
        ],
        "Tools": [
            "Audio Equipment", "Lighting Equipment", "Editing Software",
            "Musical Instruments", "Stage Props"
        ],
        "Soft Skills": [
            "Creativity", "Communication", "Teamwork", "Adaptability",
            "Time Management"
        ],
    },
    "Food and Beverage": {
        "Skills": [
            "Cooking", "Baking", "Menu Planning", "Food Safety", "Customer Service",
            "Bartending", "Inventory Management", "Culinary Techniques"
        ],
        "Tools": [
            "Kitchen Equipment", "POS Systems", "Inventory Software",
            "Food Processors", "Ovens"
        ],
        "Soft Skills": [
            "Creativity", "Time Management", "Teamwork", "Attention to Detail",
            "Adaptability"
        ],
    },
    "Real Estate": {
        "Skills": [
            "Property Management", "Sales", "Negotiation", "Market Analysis",
            "Customer Service", "Real Estate Law", "Appraisal"
        ],
        "Tools": [
            "MLS Systems", "CRM Software", "Microsoft Office", "Marketing Tools"
        ],
        "Soft Skills": [
            "Communication", "Negotiation", "Time Management", "Problem-solving",
            "Attention to Detail"
        ],
    },
    "Telecommunications": {
        "Skills": [
            "Network Engineering", "Telecom Systems", "Wireless Technologies",
            "VoIP", "Fiber Optics", "Satellite Communications", "Customer Service"
        ],
        "Tools": [
            "Network Analyzers", "Spectrum Analyzers", "Routing Equipment",
            "Cabling Tools"
        ],
        "Soft Skills": [
            "Problem-solving", "Communication", "Teamwork", "Attention to Detail",
            "Time Management"
        ],
    },
    "Pharmaceuticals": {
        "Skills": [
            "Clinical Research", "Regulatory Compliance", "Pharmacology",
            "Laboratory Skills", "Quality Assurance", "Data Analysis",
            "Drug Development"
        ],
        "Tools": [
            "Laboratory Equipment", "Statistical Software", "LIMS", "HPLC Systems"
        ],
        "Soft Skills": [
            "Attention to Detail", "Analytical Thinking", "Communication",
            "Teamwork", "Time Management"
        ],
    },
    "Aerospace": {
        "Skills": [
            "Aerodynamics", "Flight Mechanics", "Avionics", "CAD Software",
            "Structural Analysis", "Propulsion Systems", "Quality Assurance"
        ],
        "Tools": [
            "AutoCAD", "MATLAB", "Simulators", "Wind Tunnels", "Testing Equipment"
        ],
        "Soft Skills": [
            "Problem-solving", "Teamwork", "Attention to Detail", "Communication",
            "Analytical Thinking"
        ],
    },
    "Biotechnology": {
        "Skills": [
            "Molecular Biology", "Genetics", "Laboratory Techniques",
            "Data Analysis", "Regulatory Compliance", "Bioinformatics",
            "Cell Culture"
        ],
        "Tools": [
            "PCR Machines", "Microscopes", "Laboratory Equipment", "Statistical Software"
        ],
        "Soft Skills": [
            "Attention to Detail", "Analytical Thinking", "Teamwork",
            "Problem-solving", "Communication"
        ],
    },
    "Consulting": {
        "Skills": [
            "Business Analysis", "Strategic Planning", "Market Research",
            "Financial Modeling", "Process Improvement", "Project Management"
        ],
        "Tools": [
            "Microsoft Office", "CRM Software", "Data Analysis Tools", "ERP Systems"
        ],
        "Soft Skills": [
            "Communication", "Problem-solving", "Analytical Thinking", "Teamwork",
            "Time Management"
        ],
    },
    "Insurance": {
        "Skills": [
            "Risk Assessment", "Underwriting", "Claims Processing",
            "Customer Service", "Regulatory Compliance", "Sales", "Data Analysis"
        ],
        "Tools": [
            "CRM Software", "Microsoft Office", "Data Analysis Tools", "Underwriting Software"
        ],
        "Soft Skills": [
            "Attention to Detail", "Communication", "Problem-solving", "Teamwork",
            "Decision Making"
        ],
    },
    "Legal": {
        "Skills": [
            "Legal Research", "Contract Drafting", "Litigation Support",
            "Regulatory Compliance", "Client Counseling", "Case Management"
        ],
        "Tools": [
            "Legal Research Databases", "Case Management Software", "Microsoft Office"
        ],
        "Soft Skills": [
            "Attention to Detail", "Analytical Thinking", "Communication",
            "Problem-solving", "Time Management"
        ],
    },
    "Marketing and Advertising": {
        "Skills": [
            "SEO", "Content Creation", "Social Media Management", "Market Research",
            "Branding", "Copywriting", "Email Marketing", "PPC Advertising"
        ],
        "Tools": [
            "Google Analytics", "SEO Tools", "CRM Software", "Adobe Creative Suite",
            "Marketing Automation Tools"
        ],
        "Soft Skills": [
            "Creativity", "Communication", "Analytical Thinking", "Teamwork",
            "Time Management"
        ],
    },
    "Mining": {
        "Skills": [
            "Geology", "Mining Operations", "Safety Compliance", "Equipment Operation",
            "Environmental Compliance", "Resource Estimation"
        ],
        "Tools": [
            "Drilling Equipment", "Excavators", "GIS Software", "Surveying Equipment"
        ],
        "Soft Skills": [
            "Attention to Detail", "Teamwork", "Problem-solving", "Physical Stamina",
            "Time Management"
        ],
    },
    "Logistics and Supply Chain": {
        "Skills": [
            "Inventory Management", "Warehouse Operations", "Transportation Management",
            "Supply Chain Optimization", "Procurement", "Demand Forecasting"
        ],
        "Tools": [
            "ERP Systems", "Warehouse Management Systems", "Microsoft Office",
            "Transportation Management Systems"
        ],
        "Soft Skills": [
            "Problem-solving", "Communication", "Time Management", "Attention to Detail",
            "Teamwork"
        ],
    },
    "Utilities": {
        "Skills": [
            "Electrical Systems", "Plumbing", "HVAC Systems", "Maintenance",
            "Regulatory Compliance", "Safety Protocols"
        ],
        "Tools": [
            "Meters", "Hand Tools", "Diagnostic Equipment", "SCADA Systems"
        ],
        "Soft Skills": [
            "Problem-solving", "Attention to Detail", "Teamwork", "Communication",
            "Time Management"
        ],
    },
    "Fashion": {
        "Skills": [
            "Design", "Sewing", "Pattern Making", "Trend Analysis", "Merchandising",
            "Retail Management", "Branding"
        ],
        "Tools": [
            "Adobe Illustrator", "Sewing Machines", "CAD Software", "Sketching Tools"
        ],
        "Soft Skills": [
            "Creativity", "Attention to Detail", "Communication", "Time Management",
            "Teamwork"
        ],
    },
    "Sports": {
        "Skills": [
            "Coaching", "Athletic Training", "Fitness Instruction", "Event Management",
            "Team Management", "Sports Marketing"
        ],
        "Tools": [
            "Fitness Equipment", "Video Analysis Software", "CRM Software",
            "Microsoft Office"
        ],
        "Soft Skills": [
            "Leadership", "Communication", "Teamwork", "Motivation", "Adaptability"
        ],
    },
    "Environmental Services": {
        "Skills": [
            "Environmental Assessment", "Waste Management", "Sustainability Planning",
            "Regulatory Compliance", "GIS Mapping", "Data Analysis"
        ],
        "Tools": [
            "GIS Software", "Environmental Testing Equipment", "Microsoft Office",
            "Statistical Software"
        ],
        "Soft Skills": [
            "Analytical Thinking", "Attention to Detail", "Communication",
            "Problem-solving", "Teamwork"
        ],
    },
    "Architecture": {
        "Skills": [
            "Design", "CAD Software", "Building Codes", "Project Management",
            "Structural Analysis", "Sustainable Design"
        ],
        "Tools": [
            "AutoCAD", "Revit", "SketchUp", "3D Modeling Software", "Hand Drafting Tools"
        ],
        "Soft Skills": [
            "Creativity", "Attention to Detail", "Communication", "Problem-solving",
            "Teamwork"
        ],
    },
    "Arts and Culture": {
        "Skills": [
            "Painting", "Sculpture", "Art History", "Curation", "Performing Arts",
            "Photography", "Graphic Design"
        ],
        "Tools": [
            "Art Supplies", "Cameras", "Design Software", "Musical Instruments"
        ],
        "Soft Skills": [
            "Creativity", "Communication", "Time Management", "Teamwork",
            "Attention to Detail"
        ],
    },
    "Chemical Industry": {
        "Skills": [
            "Chemical Analysis", "Process Engineering", "Laboratory Techniques",
            "Safety Compliance", "Quality Control", "Research and Development"
        ],
        "Tools": [
            "Laboratory Equipment", "Chemical Reactors", "Analytical Instruments",
            "Process Simulation Software"
        ],
        "Soft Skills": [
            "Attention to Detail", "Analytical Thinking", "Problem-solving",
            "Teamwork", "Communication"
        ],
    },
    "Defense and Space": {
        "Skills": [
            "Systems Engineering", "Aerospace Engineering", "Project Management",
            "Robotics", "Cybersecurity", "Satellite Communications"
        ],
        "Tools": [
            "Simulation Software", "CAD Software", "Testing Equipment", "Encryption Tools"
        ],
        "Soft Skills": [
            "Problem-solving", "Teamwork", "Attention to Detail", "Communication",
            "Analytical Thinking"
        ],
    },
    "E-commerce": {
        "Skills": [
            "Digital Marketing", "SEO", "Content Management", "Customer Service",
            "Data Analysis", "Supply Chain Management"
        ],
        "Tools": [
            "E-commerce Platforms", "Google Analytics", "SEO Tools", "CRM Software",
            "Microsoft Office"
        ],
        "Soft Skills": [
            "Analytical Thinking", "Communication", "Problem-solving", "Teamwork",
            "Time Management"
        ],
    },
    "Human Resources": {
        "Skills": [
            "Recruitment", "Employee Relations", "Performance Management",
            "HR Compliance", "Training and Development", "Compensation and Benefits"
        ],
        "Tools": [
            "HRIS Systems", "Applicant Tracking Systems", "Microsoft Office",
            "Payroll Software"
        ],
        "Soft Skills": [
            "Communication", "Problem-solving", "Attention to Detail", "Empathy",
            "Organizational Skills"
        ],
    },
    "Information Technology Services": {
        "Skills": [
            "Network Administration", "Systems Analysis", "Technical Support",
            "Cybersecurity", "Cloud Computing", "Database Management"
        ],
        "Tools": [
            "Linux", "Windows Server", "Cisco Equipment", "VMware", "AWS", "Azure"
        ],
        "Soft Skills": [
            "Problem-solving", "Communication", "Attention to Detail", "Teamwork",
            "Time Management"
        ],
    },
    "Research and Development": {
        "Skills": [
            "Experimental Design", "Data Analysis", "Technical Writing",
            "Project Management", "Statistical Analysis", "Laboratory Techniques"
        ],
        "Tools": [
            "Statistical Software", "Laboratory Equipment", "Microsoft Office",
            "Project Management Tools"
        ],
        "Soft Skills": [
            "Analytical Thinking", "Attention to Detail", "Problem-solving",
            "Teamwork", "Communication"
        ],
    },
    # Add more industries if needed
}

# List of industries
industries = list(industry_skills.keys())

states_countries = {
    "USA": [
        "California", "New York", "Texas", "Florida", "Illinois",
        "Pennsylvania", "Ohio", "Georgia", "North Carolina", "Michigan",
        "New Jersey", "Virginia", "Washington", "Arizona", "Massachusetts",
        "Tennessee", "Indiana", "Missouri", "Maryland", "Wisconsin"
    ],
    "Canada": [
        "Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
        "Saskatchewan", "Nova Scotia", "New Brunswick",
        "Newfoundland and Labrador", "Prince Edward Island"
    ],
    "UK": ["England", "Scotland", "Wales", "Northern Ireland"],
    "Australia": [
        "New South Wales", "Victoria", "Queensland", "Western Australia",
        "South Australia", "Tasmania", "Northern Territory",
        "Australian Capital Territory"
    ],
    "Germany": [
        "Bavaria", "Baden-Württemberg", "North Rhine-Westphalia", "Hesse",
        "Saxony", "Lower Saxony", "Berlin", "Brandenburg",
        "Rhineland-Palatinate", "Thuringia"
    ],
    "France": [
        "Île-de-France", "Provence-Alpes-Côte d'Azur", "Auvergne-Rhône-Alpes",
        "Nouvelle-Aquitaine", "Occitanie", "Hauts-de-France", "Grand Est",
        "Brittany", "Normandy", "Corsica"
    ],
    "Italy": [
        "Lombardy", "Lazio", "Campania", "Sicily", "Veneto",
        "Emilia-Romagna", "Piedmont", "Tuscany", "Calabria", "Sardinia"
    ],
    "Spain": [
        "Andalusia", "Catalonia", "Madrid", "Valencian Community", "Galicia",
        "Castile and León", "Basque Country", "Canary Islands", "Murcia",
        "Aragon"
    ],
    "India": [
        "Maharashtra", "Uttar Pradesh", "Tamil Nadu", "Karnataka", "Gujarat",
        "Rajasthan", "Andhra Pradesh", "Madhya Pradesh", "West Bengal",
        "Bihar"
    ],
    "China": [
        "Guangdong", "Shandong", "Henan", "Sichuan", "Jiangsu", "Hebei",
        "Hunan", "Anhui", "Hubei", "Zhejiang"
    ]
}

genders_pronouns = {
    "Male": "he/him",
    "Female": "she/her",
    "Non-binary": "they/them",
    "Genderqueer": "they/them",
    "Transgender": "they/them",
    "Prefer not to say": ""
}

ethnicities = [
    "Caucasian", "African American", "Hispanic", "Asian", "Native American",
    "Middle Eastern", "Pacific Islander", "Multiracial", "Other",
    "Prefer not to say"
]

veteran_statuses = ["Veteran", "Non-veteran", "Prefer not to say"]

disability_statuses = ["Disabled", "Not disabled", "Prefer not to say"]

notice_periods = [
    "Immediate", "1 week", "2 weeks", "1 month", "2 months", "3 months",
    "More than 3 months"
]

salary_ranges = [
    "$20,000 - $30,000", "$30,000 - $40,000", "$40,000 - $50,000",
    "$50,000 - $60,000", "$60,000 - $70,000", "$70,000 - $80,000",
    "$80,000 - $90,000", "$90,000 - $100,000", "$100,000 - $120,000",
    "$120,000 - $150,000", "$150,000+"
]

# Generate random variables
def generate_variables():
    country = random.choice(list(states_countries.keys()))
    state = random.choice(states_countries[country])
    industry = random.choice(industries)
    gender = random.choice(list(genders_pronouns.keys()))
    
    variables = {
        'selected_country': country,
        'selected_state': state,
        'selected_industry': industry,
        'selected_gender': gender,
        'selected_pronouns': genders_pronouns[gender],
        'selected_ethnicity': random.choice(ethnicities),
        'selected_veteran_status': random.choice(veteran_statuses),
        'selected_disability_status': random.choice(disability_statuses),
        'selected_notice_period': random.choice(notice_periods),
        'selected_salary_range': random.choice(salary_ranges),
    }
    
    # Select skills appropriate for the industry
    industry_skill_categories = industry_skills[industry]
    
    selected_skills = []
    
    for category, skills_list in industry_skill_categories.items():
        num_skills = min(len(skills_list), 3)
        selected_skills.extend(random.sample(skills_list, k=random.randint(1, num_skills)))
    
    variables['selected_skills'] = selected_skills
    
    return variables

# Define the prompt template
prompt_template = """
Create a detailed job description for a random enterprise, with random information and data (all random). Include the following skills: {selected_skills}, located in {selected_state}, {selected_country}, industry: {selected_industry}, notice period: {selected_notice_period}, salary range: {selected_salary_range}.

Include the following sections in a random order, and ensure that all data corresponds to the following plaintext structure:

Provide only the plaintext code for the job description, without any explanations or additional text and also without ```markdown ```, ```json ```, ``` ```
"""

# Create the prompt and LLM chain
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

# Generate and save the curricula
num_curriculum = 50
curricula = []
# Ottieni il percorso della cartella corrente
cartella = os.path.dirname(os.path.abspath(__file__))

# Crea una nuova cartella 'jobs_descriptions' se non esiste già
cartella_jobs = os.path.join(cartella, "jobs_descriptions")
os.makedirs(cartella_jobs, exist_ok=True)

job_descriptions = []
# Genera e salva i file curriculum
for i in range(num_curriculum):
    variables = generate_variables()
    curriculum = chain.invoke(variables)  # Supponendo che questa funzione generi il curriculum in formato stringa
    filename = f"job_{i+1}.txt"
    file_path = os.path.join(cartella_jobs, filename)
    # with open(file_path, "w", encoding="utf-8") as file:
    #     file.write(curriculum)
    job_descriptions.append(curriculum)
    curricula.append(curriculum)
    # print(f"Created {file_path}")



# Step 4: Embed the job descriptions using OpenAI
response = client.embeddings.create(input=job_descriptions, model='text-embedding-ada-002')
embeddings = [v.embedding for v in response.data]

# Step 5: Connect to PostgreSQL and insert data
conn = psycopg.connect(dbname="hawk", user="user", password="pass", host="127.0.0.1", port="5432", autocommit=True)

# Register the pgvector extension
register_vector(conn)

# Create a cursor for executing SQL commands
cursor = conn.cursor()

# Ensure the table exists. You can use the following SQL schema to create it:
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_descriptions (
    id bigserial PRIMARY KEY,
    job_description text,
    embedding vector(1536)  -- Assuming OpenAI's embedding has dimension 1536
);
""")

# Step 6: Insert the job descriptions and embeddings into the table
insert_sql = """
INSERT INTO job_descriptions (job_description, embedding)
VALUES (%s, %s);
"""

for job_desc, embedding in zip(job_descriptions, embeddings):
    cursor.execute(insert_sql, (job_desc, embedding))

# Close the cursor and the connection
cursor.close()
conn.close()

print("Job descriptions and embeddings have been inserted into the database.")
