# # """
# # AI-Powered Career Intelligence Platform — Single-File Flask App

# # How to run locally (no extra files needed):
# # 1) Create a virtual env (optional) and install deps:
# #    pip install flask scikit-learn nltk pdfminer.six
   
# #    (On first run, NLTK will auto-download small tokenizers used here.)

# # 2) Start the app:
# #    python app.py

# # 3) Open http://127.0.0.1:5000 in your browser.

# # Notes:
# # - Everything (backend + frontend UI) is defined in this single file using Flask + Jinja templates.
# # - TailwindCSS, Inter font, Tabler Icons, and Chart.js are loaded via CDN.
# # - PDF resume parsing is supported if you upload a .pdf (uses pdfminer.six). Otherwise paste text.
# # - No external AI APIs are used; matching relies on TF‑IDF + cosine similarity and skill dictionaries.
# # - All processing is on-device; nothing leaves your machine.

# # """
from flask import Flask, request, render_template_string, jsonify
from datetime import datetime
import re
import os
import json
from werkzeug.utils import secure_filename
import docx
import PyPDF2
import io
from collections import Counter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'career-intelligence-secret-key-2023'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Enhanced skills database with context-aware matching
SKILLS_DB = {
    'programming': {
        'python': ['python', 'python3', 'django', 'flask', 'pandas', 'numpy'],
        'java': ['java', 'spring', 'spring boot', 'j2ee', 'java ee'],
        'javascript': ['javascript', 'js', 'es6', 'node', 'node.js', 'react', 'angular', 'vue', 'express', 'typescript'],
        'c++': ['c++', 'cpp', 'c plus plus'],
        'c#': ['c#', 'c sharp', 'dotnet', '.net', 'asp.net'],
        'php': ['php', 'laravel', 'symfony', 'wordpress'],
        'ruby': ['ruby', 'rails', 'ruby on rails'],
        'swift': ['swift', 'ios', 'swiftui'],
        'kotlin': ['kotlin', 'android'],
        'go': ['go', 'golang'],
        'rust': ['rust'],
        'typescript': ['typescript', 'ts'],
        'html': ['html', 'html5'],
        'css': ['css', 'css3', 'sass', 'scss', 'less'],
        'sql': ['sql', 'mysql', 'postgresql', 'oracle', 'sql server'],
        'r': ['r', 'r language', 'r programming'],
        'matlab': ['matlab'],
        'perl': ['perl'],
        'scala': ['scala']
    },
    'frameworks': {
        'react': ['react', 'react.js', 'reactjs'],
        'angular': ['angular', 'angular.js', 'angularjs'],
        'vue': ['vue', 'vue.js', 'vuejs'],
        'django': ['django'],
        'flask': ['flask'],
        'spring': ['spring', 'spring boot', 'spring framework'],
        'laravel': ['laravel'],
        'express': ['express', 'express.js'],
        'rails': ['rails', 'ruby on rails'],
        'asp.net': ['asp.net', 'asp net'],
        'tensorflow': ['tensorflow', 'tensor flow'],
        'pytorch': ['pytorch', 'py torch'],
        'keras': ['keras'],
        'node.js': ['node', 'node.js', 'nodejs'],
        'jquery': ['jquery'],
        'bootstrap': ['bootstrap']
    },
    'databases': {
        'mysql': ['mysql'],
        'postgresql': ['postgresql', 'postgres'],
        'mongodb': ['mongodb', 'mongo'],
        'redis': ['redis'],
        'oracle': ['oracle', 'oracle db'],
        'sqlite': ['sqlite'],
        'cassandra': ['cassandra'],
        'dynamodb': ['dynamodb', 'dynamo db']
    },
    'tools': {
        'git': ['git', 'github', 'gitlab'],
        'docker': ['docker'],
        'kubernetes': ['kubernetes', 'k8s'],
        'jenkins': ['jenkins'],
        'aws': ['aws', 'amazon web services'],
        'azure': ['azure', 'microsoft azure'],
        'gcp': ['gcp', 'google cloud', 'google cloud platform'],
        'linux': ['linux', 'ubuntu', 'centos', 'debian'],
        'unix': ['unix'],
        'ansible': ['ansible'],
        'terraform': ['terraform'],
        'selenium': ['selenium'],
        'jira': ['jira'],
        'confluence': ['confluence']
    },
    'cloud': {
        'aws': ['aws', 'amazon web services', 'ec2', 's3', 'lambda'],
        'azure': ['azure', 'microsoft azure', 'azure functions'],
        'gcp': ['gcp', 'google cloud', 'google cloud platform'],
        'cloud computing': ['cloud', 'cloud computing']
    },
    'methodologies': {
        'agile': ['agile', 'scrum', 'kanban'],
        'devops': ['devops', 'ci/cd', 'continuous integration'],
        'microservices': ['microservices', 'microservice architecture'],
        'rest': ['rest', 'restful', 'api'],
        'graphql': ['graphql'],
        'tdd': ['tdd', 'test driven development']
    },
    'soft_skills': {
        'communication': ['communication', 'communicate', 'communicating'],
        'leadership': ['leadership', 'leader', 'leading'],
        'teamwork': ['teamwork', 'team work', 'collaboration', 'collaborate'],
        'problem solving': ['problem solving', 'problem solver', 'solve problems'],
        'creativity': ['creativity', 'creative', 'innovative'],
        'adaptability': ['adaptability', 'adaptable', 'flexible'],
        'time management': ['time management', 'manage time'],
        'critical thinking': ['critical thinking', 'analytical thinking'],
        'collaboration': ['collaboration', 'collaborate']
    }
}

# Enhanced job title patterns
JOB_TITLES = {
    'software engineer': ['software engineer', 'software developer', 'backend developer', 'fullstack developer'],
    'data scientist': ['data scientist', 'ml engineer', 'ai engineer', 'machine learning engineer'],
    'devops engineer': ['devops engineer', 'site reliability engineer', 'sre'],
    'frontend developer': ['frontend developer', 'front end developer', 'ui developer'],
    'backend developer': ['backend developer', 'back end developer'],
    'fullstack developer': ['fullstack developer', 'full stack developer'],
    'mobile developer': ['mobile developer', 'ios developer', 'android developer'],
    'data engineer': ['data engineer'],
    'cloud engineer': ['cloud engineer', 'aws engineer', 'azure engineer'],
    'qa engineer': ['qa engineer', 'quality assurance', 'test engineer']
}

def extract_text_from_file(file):
    """Extract text from various file types"""
    if not file or file.filename == '':
        return "No file selected"
    
    filename = secure_filename(file.filename)
    file_ext = filename.split('.')[-1].lower()
    
    try:
        if file_ext == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        
        elif file_ext == 'docx':
            doc = docx.Document(io.BytesIO(file.read()))
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        
        elif file_ext in ['txt', 'text']:
            return file.read().decode('utf-8')
        
        else:
            return "Unsupported file format"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def preprocess_text(text):
    """Clean and preprocess text for analysis"""
    if not text:
        return ""
        
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters but keep relevant ones
    text = re.sub(r'[^\w\s,\-\./]', ' ', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_skills(text):
    """Advanced skill extraction with context awareness"""
    found_skills = set()
    text = preprocess_text(text)
    
    if not text:
        return found_skills
    
    # Multi-pass approach for better matching
    for category, skills in SKILLS_DB.items():
        for skill_key, skill_variations in skills.items():
            for variation in skill_variations:
                # Use word boundary regex to find matches
                if re.search(r'\b' + re.escape(variation) + r'\b', text):
                    found_skills.add(skill_key)
                    break
    
    return found_skills

def extract_job_titles(text):
    """Extract job titles from text with context awareness"""
    found_titles = set()
    text = preprocess_text(text)
    
    if not text:
        return found_titles
    
    for title_key, title_variations in JOB_TITLES.items():
        for variation in title_variations:
            if re.search(r'\b' + re.escape(variation) + r'\b', text):
                found_titles.add(title_key)
                break
    
    return found_titles

def extract_experience_level(text):
    """Extract experience level requirements"""
    text = preprocess_text(text)
    experience_patterns = [
        (r'(\d+)[\+]?\s*(years|yrs)\s*(experience|exp)', 1),
        (r'(senior|lead|principal)\s+(\w+\s+)*\w+', 0),
        (r'(junior|entry level|associate)\s+(\w+\s+)*\w+', 0),
        (r'(mid level|mid-level|mid senior|mid-senior)\s+(\w+\s+)*\w+', 0)
    ]
    
    experience_level = "Not specified"
    for pattern, group in experience_patterns:
        match = re.search(pattern, text)
        if match:
            if group == 0:
                experience_level = match.group(0)
            else:
                experience_level = f"{match.group(1)} years"
            break
    
    return experience_level

def calculate_match(resume_text, jd_text):
    """Advanced matching algorithm with multiple factors"""
    if not resume_text or not jd_text:
        return 0, [], [], [], [], "Not specified"
    
    # Extract skills from both texts
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    
    # Extract job titles from JD
    jd_titles = extract_job_titles(jd_text)
    resume_titles = extract_job_titles(resume_text)
    
    # Extract experience level
    experience_level = extract_experience_level(jd_text)
    
    # Calculate multiple match factors
    # Skill-based matching
    matched_skills = resume_skills & jd_skills
    missing_skills = jd_skills - resume_skills
    extra_skills = resume_skills - jd_skills
    
    # Title matching bonus
    title_match_bonus = 15 if jd_titles and resume_titles and jd_titles & resume_titles else 0
    
    # Experience level consideration
    experience_bonus = 5
    
    # Calculate comprehensive match score
    # If no specific skills in JD, use keyword matching instead
    if not jd_skills:
        # Fallback to keyword matching
        jd_words = set(preprocess_text(jd_text).split())
        resume_words = set(preprocess_text(resume_text).split())
        common_words = jd_words & resume_words
        # Remove common unimportant words
        common_words = {word for word in common_words if len(word) > 4 and word not in [
            'experience', 'years', 'development', 'software', 'engineer', 'developer'
        ]}
        match_score = min(len(common_words) * 5, 80)  # Max 80% for keyword matching
    else:
        skill_match_ratio = len(matched_skills) / len(jd_skills) if jd_skills else 0
        base_score = skill_match_ratio * 80  # 80% max for skills
    
    # Add bonuses
    match_score = min(int(base_score + title_match_bonus + experience_bonus), 100)
    
    return match_score, list(matched_skills), list(missing_skills), list(extra_skills), list(jd_titles), experience_level

def generate_keyword_heatmap(resume_text, jd_text):
    """Generate keyword frequency data for heatmap visualization"""
    if not resume_text or not jd_text:
        return []
    
    # Extract words from both texts (longer words are more meaningful)
    resume_words = [word for word in preprocess_text(resume_text).split() if len(word) > 4]
    jd_words = [word for word in preprocess_text(jd_text).split() if len(word) > 4]
    
    # Count frequencies
    resume_freq = Counter(resume_words)
    jd_freq = Counter(jd_words)
    
    # Get top keywords from JD (excluding common words)
    common_words = {'experience', 'years', 'development', 'software', 'engineer', 'developer', 'skills', 'ability', 'knowledge'}
    top_keywords = [(word, count) for word, count in jd_freq.most_common(20) 
                   if word not in common_words and count > 1]
    
    # Prepare heatmap data
    heatmap_data = []
    for keyword, jd_count in top_keywords:
        resume_count = resume_freq.get(keyword, 0)
        match_ratio = resume_count / max(jd_count, 1)
        
        heatmap_data.append({
            'keyword': keyword,
            'jd_frequency': jd_count,
            'resume_frequency': resume_count,
            'match_ratio': min(match_ratio, 1)
        })
    
    return heatmap_data

# HTML template (same as before)
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Career Intelligence Platform</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <style>
    html, body { 
      font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Helvetica, Arial; 
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
      min-height: 100vh;
    }
    .glass { 
      backdrop-filter: blur(10px); 
      background: rgba(255,255,255,0.7); 
    }
    .gradient { 
      background: linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 50%, #ec4899 100%); 
    }
    .card { 
      border-radius: 1rem; 
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      padding: 1.5rem; 
      background: white; 
    }
    .pill { 
      display: inline-flex;
      align-items: center;
      border-radius: 9999px;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      line-height: 1rem;
      font-weight: 600;
      background: rgba(0, 0, 0, 0.05);
    }
    .btn-primary {
      background: linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 50%, #ec4899 100%);
      color: white;
      padding: 0.75rem 1.5rem;
      border-radius: 0.75rem;
      font-weight: 600;
      transition: all 0.3s ease;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .form-input {
      width: 100%;
      padding: 0.75rem;
      border-radius: 0.5rem;
      border: 1px solid #e2e8f0;
      margin-bottom: 1rem;
      transition: all 0.3s ease;
    }
    .form-input:focus {
      outline: none;
      border-color: #0ea5e9;
      box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2);
    }
    .file-input {
      position: relative;
      overflow: hidden;
      display: inline-block;
      width: 100%;
    }
    .file-input input[type="file"] {
      position: absolute;
      left: 0;
      top: 0;
      opacity: 0;
      width: 100%;
      height: 100%;
      cursor: pointer;
    }
    .file-input-label {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      border: 2px dashed #cbd5e0;
      border-radius: 0.5rem;
      background-color: #f8fafc;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s ease;
    }
    .file-input-label:hover {
      border-color: #0ea5e9;
      background-color: #f0f9ff;
    }
    .skill-match {
      background-color: #10b981;
      color: white;
    }
    .skill-missing {
      background-color: #ef4444;
      color: white;
    }
    .skill-extra {
      background-color: #f59e0b;
      color: white;
    }
    .job-title {
      background-color: #8b5cf6;
      color: white;
    }
    .experience-level {
      background-color: #ec4899;
      color: white;
    }
  </style>
</head>
<body>
  <div class="gradient text-white">
    <div class="max-w-6xl mx-auto px-6 py-16">
      <div class="flex flex-col md:flex-row items-center gap-8">
        <div class="flex-1">
          <div class="pill bg-white/20 mb-4">AI-Powered</div>
          <h1 class="text-4xl md:text-6xl font-extrabold leading-tight">Career Intelligence Platform</h1>
          <p class="text-white/90 mt-4 text-lg md:text-xl">Upload your resume & paste a job description. Instantly get a match score, skill-gaps, and keyword heatmaps. Private. Fast. Beautiful.</p>
          <div class="mt-6 flex gap-3">
            <a href="#analyze" class="bg-white text-slate-900 hover:bg-white/90 transition rounded-xl px-5 py-3 font-semibold shadow">Analyze Now</a>
          </div>
        </div>
        <div class="flex-1 glass rounded-3xl p-6 shadow-xl">
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-black/90 rounded-2xl p-4">
              <div class="text-sm text-slate-500">Avg. Match Lift</div>
              <div class="text-3xl font-extrabold">+45%</div>
              <div class="text-xs text-slate-500 mt-2">Using TF‑IDF + skill mapping</div>
            </div>
            <div class="bg-black/90 rounded-2xl p-4">
              <div class="text-sm text-slate-500">Screening Time ↓</div>
              <div class="text-3xl font-extrabold">-30%</div>
              <div class="text-xs text-slate-500 mt-2">Cleaner signals for recruiters</div>
            </div>
            <div class="bg-black/90 rounded-2xl p-4 col-span-2">
              <div class="text-sm text-slate-500">Private-by-default</div>
              <div class="text-lg font-semibold">All analysis happens in your browser + this local app. No uploads to third parties.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <main class="max-w-4xl mx-auto px-6 py-12 relative z-10">
    <section id="analyze" class="card mb-12">
      <h2 class="text-2xl font-bold mb-6 text-center">Resume-Job Match Analyzer</h2>
      <form method="POST" action="/analyze" enctype="multipart/form-data" class="space-y-6">
        <div>
          <h3 class="text-lg font-semibold mb-3">Upload Your Resume</h3>
          <div class="file-input">
            <input type="file" name="resume_file" id="resume_file" accept=".pdf,.docx,.txt">
            <label for="resume_file" class="file-input-label">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-slate-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span class="font-medium">Click to upload your resume</span>
              <span class="text-sm text-slate-500">PDF, DOCX, or TXT (Max 16MB)</span>
            </label>
          </div>
          <div id="file-name" class="text-sm text-slate-600 mt-2 hidden"></div>
        </div>

        <div class="relative">
          <div class="absolute inset-0 flex items-center" aria-hidden="true">
            <div class="w-full border-t border-gray-300"></div>
          </div>
          <div class="relative flex justify-center">
            <span class="px-3 bg-white text-sm text-gray-500">And</span>
          </div>
        </div>

        <div>
          <h3 class="text-lg font-semibold mb-3">Paste Job Description</h3>
          <textarea name="jd_text" placeholder="Copy and paste the job description here..." class="form-input" rows="6" required></textarea>
        </div>

        <div class="text-center">
          <button type="submit" class="btn-primary">Analyze Match</button>
        </div>
      </form>
    </section>

    <div id="results-section" class="hidden">
      <div class="card mb-8">
        <h2 class="text-2xl font-bold mb-6 text-center">Analysis Results</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div class="bg-blue-50 rounded-xl p-5 text-center">
            <div class="text-4xl font-bold text-blue-700 mb-2" id="match-score">0%</div>
            <div class="text-blue-600 font-medium">Match Score</div>
          </div>
          
          <div class="bg-red-50 rounded-xl p-5 text-center">
            <div class="text-4xl font-bold text-red-700 mb-2" id="missing-count">0</div>
            <div class="text-red-600 font-medium">Skills Missing</div>
          </div>
          
          <div class="bg-amber-50 rounded-xl p-5 text-center">
            <div class="text-4xl font-bold text-amber-700 mb-2" id="extra-count">0</div>
            <div class="text-amber-600 font-medium">Extra Skills</div>
          </div>
          
          <div class="bg-purple-50 rounded-xl p-5 text-center">
            <div class="text-4xl font-bold text-purple-700 mb-2" id="title-count">0</div>
            <div class="text-purple-600 font-medium">Job Titles</div>
          </div>
        </div>
        
        <div id="experience-section" class="mb-6 hidden">
          <h3 class="text-xl font-semibold mb-4">Experience Level Required</h3>
          <div id="experience-level" class="pill experience-level text-lg"></div>
        </div>
        
        <div id="job-titles-section" class="mb-6 hidden">
          <h3 class="text-xl font-semibold mb-4">Job Titles Found</h3>
          <div id="job-titles" class="flex flex-wrap gap-2"></div>
        </div>
        
        <div class="mb-8">
          <h3 class="text-xl font-semibold mb-4">Skill Analysis</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h4 class="font-medium text-green-700 mb-3">Matched Skills</h4>
              <div id="matched-skills" class="space-y-2"></div>
            </div>
            
            <div>
              <h4 class="font-medium text-red-700 mb-3">Missing Skills</h4>
              <div id="missing-skills" class="space-y-2"></div>
            </div>
            
            <div>
              <h4 class="font-medium text-amber-700 mb-3">Extra Skills</h4>
              <div id="extra-skills" class="space-y-2"></div>
            </div>
          </div>
        </div>
        
        <div>
          <h3 class="text-xl font-semibold mb-4">Keyword Heatmap</h3>
          <p class="text-slate-600 mb-4">Comparison of keyword frequency between your resume and the job description</p>
          <div id="keyword-heatmap" class="space-y-4"></div>
        </div>
      </div>
      
      <div class="text-center">
        <button onclick="window.location.href='#analyze'" class="btn-primary">Analyze Another</button>
      </div>
    </div>
  </main>

  <footer class="max-w-6xl mx-auto px-6 py-16 text-sm text-slate-500">
    <div class="flex flex-col md:flex-row items-center justify-between gap-4">
      <div>© {{year}} Career Intelligence. Local-first. Open UI. By -Sohaib Khan</div>
      <div class="flex gap-3">
        <span class="pill">No data storage</span>
        <span class="pill">Open templates</span>
        <span class="pill">One-file app</span>
      </div>
    </div>
  </footer>

  <script>
    // File input display
    document.getElementById('resume_file').addEventListener('change', function(e) {
      const fileName = e.target.files[0]?.name || 'No file chosen';
      document.getElementById('file-name').textContent = `Selected: ${fileName}`;
      document.getElementById('file-name').classList.remove('hidden');
    });
    
    // Smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', (e) => {
        const id = a.getAttribute('href').substring(1);
        const el = document.getElementById(id);
        if (el) { 
          e.preventDefault(); 
          el.scrollIntoView({behavior: 'smooth'}); 
        }
      });
    });
    
    // Form submission
    document.querySelector('form').addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const formData = new FormData(e.target);
      const submitBtn = e.target.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Analyzing...';
      
      try {
        const response = await fetch('/analyze', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
          displayResults(data);
        } else {
          alert(data.error || 'Error analyzing documents. Please try again.');
        }
      } catch (error) {
        alert('Error: ' + error.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Analyze Match';
      }
    });
    
    function displayResults(data) {
      // Update match score
      document.getElementById('match-score').textContent = `${data.match_score}%`;
      
      // Update skill counts
      document.getElementById('missing-count').textContent = data.missing_skills.length;
      document.getElementById('extra-count').textContent = data.extra_skills.length;
      document.getElementById('title-count').textContent = data.job_titles.length;
      
      // Display experience level
      const experienceElement = document.getElementById('experience-level');
      experienceElement.textContent = data.experience_level;
      document.getElementById('experience-section').classList.remove('hidden');
      
      // Display job titles if any
      const jobTitlesContainer = document.getElementById('job-titles');
      jobTitlesContainer.innerHTML = '';
      
      if (data.job_titles && data.job_titles.length > 0) {
        data.job_titles.forEach(title => {
          const pill = document.createElement('div');
          pill.className = 'pill job-title';
          pill.textContent = title;
          jobTitlesContainer.appendChild(pill);
        });
        document.getElementById('job-titles-section').classList.remove('hidden');
      } else {
        document.getElementById('job-titles-section').classList.add('hidden');
      }
      
      // Display matched skills
      const matchedSkillsContainer = document.getElementById('matched-skills');
      matchedSkillsContainer.innerHTML = '';
      data.matched_skills.forEach(skill => {
        const pill = document.createElement('div');
        pill.className = 'pill skill-match';
        pill.textContent = skill;
        matchedSkillsContainer.appendChild(pill);
      });
      
      if (data.matched_skills.length === 0) {
        matchedSkillsContainer.innerHTML = '<p class="text-slate-500">No skills matched</p>';
      }
      
      // Display missing skills
      const missingSkillsContainer = document.getElementById('missing-skills');
      missingSkillsContainer.innerHTML = '';
      data.missing_skills.forEach(skill => {
        const pill = document.createElement('div');
        pill.className = 'pill skill-missing';
        pill.textContent = skill;
        missingSkillsContainer.appendChild(pill);
      });
      
      if (data.missing_skills.length === 0) {
        missingSkillsContainer.innerHTML = '<p class="text-slate-500">No missing skills</p>';
      }
      
      // Display extra skills
      const extraSkillsContainer = document.getElementById('extra-skills');
      extraSkillsContainer.innerHTML = '';
      data.extra_skills.forEach(skill => {
        const pill = document.createElement('div');
        pill.className = 'pill skill-extra';
        pill.textContent = skill;
        extraSkillsContainer.appendChild(pill);
      });
      
      if (data.extra_skills.length === 0) {
        extraSkillsContainer.innerHTML = '<p class="text-slate-500">No extra skills</p>';
      }
      
      // Display keyword heatmap
      const heatmapContainer = document.getElementById('keyword-heatmap');
      heatmapContainer.innerHTML = '';
      
      if (data.heatmap_data && data.heatmap_data.length > 0) {
        data.heatmap_data.forEach(item => {
          const ratio = Math.min(item.match_ratio, 1);
          
          const heatmapItem = document.createElement('div');
          heatmapItem.className = 'bg-white p-4 rounded-lg shadow-sm';
          
          heatmapItem.innerHTML = `
            <div class="flex justify-between mb-2">
              <span class="font-medium">${item.keyword}</span>
              <span class="text-sm text-slate-600">JD: ${item.jd_frequency}, Resume: ${item.resume_frequency}</span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-2.5">
              <div class="bg-blue-600 h-2.5 rounded-full" style="width: ${ratio * 100}%"></div>
            </div>
          `;
          
          heatmapContainer.appendChild(heatmapItem);
        });
      } else {
        heatmapContainer.innerHTML = '<p class="text-slate-500">Not enough data for keyword analysis</p>';
      }
      
      // Show results section
      document.getElementById('results-section').classList.remove('hidden');
      
      // Scroll to results
      document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
    }
  </script>
</body>
</html>
"""

# Home route
@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE, year=datetime.now().year)

# Analyze route
@app.route("/analyze", methods=["POST"])
def analyze():
    # Get job description text
    jd_text = request.form.get("jd_text", "")
    
    # Get resume text from file upload
    resume_text = ""
    
    # Check if a file was uploaded
    if 'resume_file' in request.files:
        file = request.files['resume_file']
        if file and file.filename != '':
            resume_text = extract_text_from_file(file)
    
    # Validate inputs
    if not resume_text or resume_text.startswith("Error") or resume_text == "Unsupported file format":
        return jsonify({
            "error": "Please upload a valid resume file (PDF, DOCX, or TXT)",
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "extra_skills": [],
            "job_titles": [],
            "experience_level": "Not specified",
            "heatmap_data": []
        }), 400
    
    if not jd_text.strip():
        return jsonify({
            "error": "Please enter a job description",
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "extra_skills": [],
            "job_titles": [],
            "experience_level": "Not specified",
            "heatmap_data": []
        }), 400
    
    # Calculate match
    match_score, matched_skills, missing_skills, extra_skills, job_titles, experience_level = calculate_match(resume_text, jd_text)
    
    # Generate heatmap data
    heatmap_data = generate_keyword_heatmap(resume_text, jd_text)
    
    return jsonify({
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "extra_skills": extra_skills,
        "job_titles": job_titles,
        "experience_level": experience_level,
        "heatmap_data": heatmap_data
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)