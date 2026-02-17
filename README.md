# 🏥 PharmacyAI - Agentic Generative AI Online Pharmacy Platform

A comprehensive, production-ready AI-powered online pharmacy platform built with a multi-agent architecture. The system uses autonomous AI agents to assist customers with medicine search, prescription validation, order processing, and more.

## 🌟 Features

### Customer Features
- **AI-Powered Chat**: Natural language medicine search and health queries
- **Prescription Upload**: Secure upload and AI validation of prescriptions (image/PDF)
- **Smart Recommendations**: Safe OTC medicine recommendations with drug interaction checks
- **Order Management**: Complete order lifecycle from cart to delivery
- **Real-time Tracking**: Track shipments and order status

### Pharmacist Features
- **Prescription Review Dashboard**: Queue-based prescription approval workflow
- **AI-Assisted Review**: Automated flagging of potential issues
- **Inventory Alerts**: Low stock and expiry notifications

### Admin Features
- **Medicine Catalog Management**: CRUD operations for medicines and categories
- **User Management**: Customer, pharmacist, and admin role management
- **Sales Analytics**: Dashboard with key metrics and reports
- **Agent Logs**: Monitor AI agent performance and actions

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR AGENT                        │
│                    (Central Controller)                          │
└─────────────┬───────────────────────────────────────────────────┘
              │
    ┌─────────┼─────────┬──────────┬──────────┬──────────┐
    │         │         │          │          │          │
    ▼         ▼         ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Customer│ │Medicine│ │Prescription│ │Inventory│ │ Order  │ │Compliance│
│Support │ │Search  │ │Validation │ │Management│ │Processing│ │  & Safety│
└──────┘ └──────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| **Backend** | Python 3.11, FastAPI, Pydantic |
| **Database** | PostgreSQL 15 (primary), Redis (cache/sessions) |
| **AI/LLM** | OpenAI GPT-4, LangChain, Vector Embeddings |
| **Vector DB** | Pinecone / FAISS |
| **Storage** | AWS S3 / MinIO (prescriptions) |
| **Queue** | Celery + Redis |
| **Deployment** | Docker, Docker Compose |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd pharmacy-ai-platform

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Access the Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## 🛠️ Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 📁 Project Structure

```
pharmacy-ai-platform/
├── backend/
│   ├── app/
│   │   ├── agents/          # AI Agent implementations
│   │   │   ├── base.py      # Base agent class
│   │   │   ├── orchestrator.py
│   │   │   ├── customer_support.py
│   │   │   ├── medicine_search.py
│   │   │   ├── prescription_validation.py
│   │   │   ├── order_processing.py
│   │   │   └── compliance_safety.py
│   │   ├── api/             # API routes
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── medicines.py
│   │   │   └── prescriptions.py
│   │   ├── core/            # Configuration
│   │   ├── db/              # Database models
│   │   ├── models/          # SQLAlchemy models
│   │   └── main.py          # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── contexts/        # React contexts
│   │   ├── layouts/         # Page layouts
│   │   ├── pages/           # Page components
│   │   └── App.tsx          # Main app
│   └── package.json
├── database/
│   └── schema.sql           # PostgreSQL schema
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

## 🔐 Security Features

- **JWT Authentication**: Secure token-based auth with refresh tokens
- **Role-Based Access Control**: Customer, Pharmacist, Admin roles
- **PII Encryption**: Sensitive data encrypted at rest
- **HIPAA Compliance**: Audit logs, data retention policies
- **Rate Limiting**: API rate limiting per user/IP
- **Input Validation**: Pydantic models for all inputs
- **CORS Protection**: Configurable CORS policies

## 🤖 AI Agent System

### Agent Types

1. **Orchestrator Agent**: Routes requests to appropriate specialized agents
2. **Customer Support Agent**: Handles general inquiries and FAQs
3. **Medicine Search Agent**: Semantic search and recommendations
4. **Prescription Validation Agent**: OCR-based prescription validation
5. **Order Processing Agent**: Order creation and management
6. **Compliance & Safety Agent**: Drug interaction checks, PII detection

### Agent Communication

Agents communicate via a message bus architecture using Redis:

```python
# Example: Routing a prescription upload
user_request → Orchestrator → PrescriptionValidationAgent
                                    ↓
                           PharmacistReviewAgent (if needed)
                                    ↓
                           MedicineSearchAgent (for recommendations)
```

## 📊 Database Schema

### Core Tables
- `users`: Customer, pharmacist, and admin accounts
- `medicines`: Medicine catalog with details
- `prescriptions`: Prescription records with validation status
- `orders`: Order headers and items
- `payments`: Payment transactions
- `conversations`: Chat history
- `agent_logs`: AI agent action audit trail

See `database/schema.sql` for complete schema.

## 🔌 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user

### Chat
- `POST /chat/message` - Send message to AI
- `GET /chat/conversations` - Get conversation history
- `WS /chat/ws/{user_id}` - WebSocket for real-time chat

### Medicines
- `GET /medicines` - List medicines
- `GET /medicines/search?q={query}` - Search medicines
- `GET /medicines/{id}` - Get medicine details

### Prescriptions
- `POST /prescriptions/upload` - Upload prescription
- `GET /prescriptions` - List prescriptions
- `GET /prescriptions/{id}` - Get prescription details

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up
```

## 📈 Monitoring & Observability

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **Structured Logging**: JSON logs with correlation IDs
- **Distributed Tracing**: OpenTelemetry integration

## 🚢 Deployment

### Production Checklist

- [ ] Change default passwords and secrets
- [ ] Configure SSL/TLS certificates
- [ ] Set up proper CORS origins
- [ ] Configure production database
- [ ] Set up backup strategies
- [ ] Configure monitoring and alerting
- [ ] Enable rate limiting
- [ ] Review security headers

### Kubernetes Deployment

```yaml
# See k8s/ directory for Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This is a demonstration application for educational purposes. It is not a real pharmacy and should not be used for actual medical advice or medication purchases. Always consult licensed healthcare professionals for medical needs.


Built with ❤️ using FastAPI, React, and OpenAI
