\# Sentinel Eye



\## Biometric Face Search, Watchlist Matching \& Alert System



Sentinel Eye is a biometric face-search system designed as a graduation project. The system allows a user to register watchlist identities, upload a face image for searching, compare the uploaded image against stored face embeddings, and generate alerts when a possible match is found.



The project focuses on facial image retrieval using deep face embeddings, masked-face recognition, vector similarity search, and a security-style dashboard.



\---



\## Project Idea



Traditional face recognition systems may perform poorly when the input image contains a mask, low-quality face, different lighting, or a different angle. Sentinel Eye solves this by converting faces into numerical embedding vectors and comparing these vectors using similarity search.



The main workflow is:



```text

Upload image

→ Detect and align face

→ Extract face embedding using FocusFace

→ Search stored embeddings using vector similarity

→ Return top matches and confidence score

→ Generate alert if match is strong enough

```



The system is not connected to any real criminal or Interpol database. It uses simulated watchlist identities and public/research dataset images for academic purposes only.



\---



\## Main Features



\* Register a watchlist identity using a face image

\* Search an uploaded face against the watchlist

\* Masked-face recognition using FocusFace embeddings

\* FAISS vector search for scalable nearest-neighbor retrieval

\* Cosine similarity fallback if FAISS is not available

\* Display best match, score, confidence, and alert level

\* Show top matching identities

\* Robust mode for masked or unclear faces

\* Camera/location simulation

\* Alert history

\* Search history

\* Dashboard statistics

\* RMFRD/AFDB dataset evaluation

\* Top-1 and Top-3 accuracy calculation



\---



\## Tech Stack



\### Backend



\* Python

\* FastAPI

\* SQLite

\* NumPy

\* FAISS

\* FocusFace

\* DeepFace / RetinaFace for face detection and alignment

\* Uvicorn



\### Frontend



\* React

\* Vite

\* JavaScript

\* HTML/CSS



\### AI / Machine Learning



\* FocusFace pretrained masked-face recognition model

\* Face embeddings

\* Vector similarity search

\* FAISS IndexFlatIP

\* Cosine similarity



\---



\## System Architecture



```text

React Frontend

&#x20;   |

&#x20;   | HTTP Requests

&#x20;   v

FastAPI Backend

&#x20;   |

&#x20;   | Face image processing

&#x20;   v

FocusFace Model

&#x20;   |

&#x20;   | Embedding vector

&#x20;   v

FAISS / Cosine Similarity Search

&#x20;   |

&#x20;   | Top matches

&#x20;   v

SQLite Database + Alert History

```



\---



\## Project Structure



```text

DEPI-Final-Project\_ML-main/

│

├── backend/

│   ├── main.py

│   ├── focusface\_engine.py

│   ├── biometric.db

│   ├── requirements.txt

│   └── venv/

│

├── frontend/

│   ├── src/

│   │   ├── App.jsx

│   │   ├── App.css

│   │   └── main.jsx

│   ├── package.json

│   └── node\_modules/

│

├── focusface/

│   ├── FocusFace/

│   └── weights/

│       └── focus\_face\_w\_pretrained.mdl

│

├── dataset/

│   └── RMFRD/

│       ├── unmasked/

│       └── masked/

│

├── test\_images/

├── focusface\_test.py

├── prepare\_dataset\_subset.py

├── evaluate\_rmfrd.py

├── evaluate\_rmfrd\_faiss.py

├── make\_evaluation\_chart.py

├── rmfrd\_results.csv

├── rmfrd\_faiss\_results.csv

└── README.md

```



\---



\## AI Model Used



The project uses \*\*FocusFace\*\*, a pretrained masked-face recognition model. FocusFace is used to extract face embeddings from uploaded images.



A face embedding is a numerical vector that represents the identity-related features of a face. Instead of comparing images directly, the system compares embeddings.



Example:



```text

Face image → FocusFace → Embedding vector

```



Then the backend compares the query embedding with stored watchlist embeddings.



\---



\## Search Method



The system uses vector similarity search.



\### Current Search Method



```text

FAISS Vector Search

```



FAISS is used to search for the nearest stored face embeddings efficiently. The implementation uses `IndexFlatIP`, which performs inner-product search. Since embeddings are normalized, inner product works like cosine similarity.



\### Fallback Search Method



```text

Cosine Similarity Fallback

```



If FAISS is not installed or not available, the backend can still compare embeddings using cosine similarity.



\---



\## Dataset Evaluation



The system was evaluated using a subset of the RMFRD/AFDB masked-face dataset.



\### Evaluation Setup



```text

Unmasked images → Gallery / Watchlist

Masked images → Test / Probe images

```



The system compares each masked test image with the stored unmasked gallery embeddings.



\### Evaluation Metrics



\* \*\*Top-1 Accuracy\*\*: The correct identity is the first returned result.

\* \*\*Top-3 Accuracy\*\*: The correct identity appears within the top 3 returned results.



\### Results



| Setup                       | Top-1 Accuracy | Top-3 Accuracy |

| --------------------------- | -------------: | -------------: |

| 1 image per identity        |         26.32% |         47.37% |

| Up to 5 images per identity |         48.28% |         65.52% |



\### Final Evaluation Result



```text

Dataset: RMFRD / AFDB subset

Model: FocusFace

Search Method: FAISS Vector Search

Total Tests: 29

Top-1 Accuracy: 48.28%

Top-3 Accuracy: 65.52%

```



Using multiple gallery images per identity improved the retrieval performance because the system had more face variations for each person.



\---



\## How to Run the Project



\### 1. Clone or Open the Project



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main

```



\---



\## Backend Setup



Go to the backend folder:



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main\\backend

```



Activate the virtual environment:



```powershell

.\\venv\\Scripts\\Activate.ps1

```



Install required packages:



```powershell

pip install -r requirements.txt

```



Run the backend server:



```powershell

python -m uvicorn main:app --reload

```



Backend URL:



```text

http://127.0.0.1:8000

```



API documentation:



```text

http://127.0.0.1:8000/docs

```



\---



\## Frontend Setup



Open a new terminal and go to the frontend folder:



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main\\frontend

```



Install frontend dependencies:



```powershell

npm install

```



Run the frontend:



```powershell

npm run dev

```



Frontend URL is usually:



```text

http://localhost:5173

```



\---



\## Main Daily Run Commands



\### Run Backend



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main\\backend

.\\venv\\Scripts\\Activate.ps1

python -m uvicorn main:app --reload

```



\### Run Frontend



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main\\frontend

npm run dev

```



\---



\## FocusFace Model Setup



The FocusFace repository should be placed inside:



```text

focusface/FocusFace

```



The pretrained model weight should be placed inside:



```text

focusface/weights/focus\_face\_w\_pretrained.mdl

```



Command used to download the pretrained weight:



```powershell

python -c "from huggingface\_hub import hf\_hub\_download; hf\_hub\_download(repo\_id='netopedro/FocusFace', filename='focus\_face\_w\_pretrained.mdl', local\_dir='weights')"

```



Because the model file is large, it should not be uploaded directly to GitHub unless Git LFS is used.



\---



\## Testing FocusFace Manually



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main

.\\backend\\venv\\Scripts\\Activate.ps1

python .\\focusface\_test.py .\\test\_images\\mbappe\_clear.jpg .\\test\_images\\mbappe\_masked.jpg

```



\---



\## Running Dataset Evaluation



\### Normal Evaluation



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main

.\\backend\\venv\\Scripts\\Activate.ps1

python evaluate\_rmfrd.py

```



\### FAISS Evaluation



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main

.\\backend\\venv\\Scripts\\Activate.ps1

python evaluate\_rmfrd\_faiss.py

```



Expected output includes:



```text

Total tests: 29

Top-1 Accuracy: 48.28%

Top-3 Accuracy: 65.52%

```



\---



\## Checking FAISS



To check if FAISS is installed correctly:



```powershell

cd C:\\Users\\lenvo\\Desktop\\DEPI-Final-Project\_ML-main\\backend

.\\venv\\Scripts\\Activate.ps1

python -c "import faiss; print('FAISS OK')"

```



Expected output:



```text

FAISS OK

```



\---



\## Important Notes



\* FAISS improves retrieval scalability, not recognition accuracy.

\* FocusFace embedding extraction is the slowest part of evaluation.

\* FAISS is more useful when the system stores thousands or millions of embeddings.

\* In this prototype, FAISS and cosine similarity may produce the same accuracy because `IndexFlatIP` is an exact vector search method.

\* The current project uses simulated watchlist identities for academic purposes only.

\* The system should not be used for real surveillance or real law-enforcement decisions without proper legal, ethical, and security controls.



\---



\## Limitations



\* The system performance depends on image quality, lighting, face angle, and mask coverage.

\* Masked-face recognition is harder than normal face recognition because part of the face is hidden.

\* The prototype uses a limited dataset subset for evaluation.

\* The current system is mainly for academic demonstration.

\* Real deployment would require stronger authentication, access control, audit logs, privacy protection, and legal approval.



\---



\## Future Work



Possible future improvements include:



\* Authentication and role-based access control

\* Admin-only identity management

\* Real-time camera stream integration

\* Larger dataset evaluation

\* More advanced vector databases such as Milvus or Pinecone

\* Cloud deployment on Azure

\* Improved UI analytics and charts

\* Audit logging for all security-sensitive actions

\* Human review workflow for low-confidence matches



\---



\## Demo Scenario



Recommended demo flow:



```text

1\. Open the Sentinel Eye dashboard.

2\. Register a clear face image as a watchlist identity.

3\. Upload a masked or unclear face image for searching.

4\. Show the best match, score, confidence, and alert level.

5\. Show top matches.

6\. Show camera/location simulation.

7\. Show alert history and search history.

8\. Mention RMFRD/AFDB evaluation results.

9\. Mention FAISS as the scalable vector search method.

```



\---



\## Project Summary



Sentinel Eye demonstrates a complete biometric face-search pipeline. It combines face embedding extraction, masked-face recognition, vector similarity search, FAISS retrieval, alert generation, and evaluation using a masked-face dataset. The project shows how AI-based biometric retrieval can be implemented as a scalable prototype while also highlighting the importance of privacy, security, and responsible usage.



