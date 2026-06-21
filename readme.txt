🚀 4. How to Run Locally
You will need two separate terminal windows—one for the FastAPI backend and one for the React frontend. Note that the very first run of the backend might take a couple of minutes to execute an API endpoint because the deepface library will automatically download the Facenet pre-trained ML weights.

Terminal 1: Start the Backend

powershell
# 1. Navigate to the backend folder
cd "d:\biometric project\backend"
# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
.\venv\Scripts\activate
# 3. Install the dependencies
pip install -r requirements.txt
# 4. Start the FastAPI server
uvicorn main:app --reload
The backend API will run natively at http://localhost:8000.

Terminal 2: Start the Frontend

powershell
# 1. Navigate to the frontend folder
cd "d:\biometric project\frontend"
# 2. Install the necessary Node packages (including Tailwind CSS that I preconfigured)
npm install
# 3. Start the Vite development server
npm run dev
The React development server will start instantly and provide you with a localhost URL (usually http://localhost:5173). Click the link to view the sleek new web app and begin uploading profile photos!