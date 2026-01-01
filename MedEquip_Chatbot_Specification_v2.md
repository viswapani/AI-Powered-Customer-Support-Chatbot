# MedEquip AI Chatbot - Development Plan

## Project Overview
Build a real-time AI-powered customer support chatbot for MedEquip Solutions, a healthcare equipment manufacturing company. The system uses a hybrid SQL + RAG approach to handle 9 distinct customer support use cases with authentication and compliance considerations.

---

## Phase 1: Environment Setup & Dependencies

### Install Required Packages
```bash
pip install openai langchain langchain-openai langchain-community chromadb faker pandas sqlalchemy
```

### Configure API Keys
```bash
export OPENAI_API_KEY="your-key-here"
```

### Create Project Structure
```bash
mkdir -p medequip_chatbot
cd medequip_chatbot
mkdir -p data vectorstore tests
touch chatbot.py database.py rag_pipeline.py config.py test_scenarios.py
```

---

## Phase 2: Database Implementation

### Create SQLite Database Schema
**File**: `database.py`

#### Tables to Implement (17 total):
1. **clients** - Customer information and authentication
2. **products** - Equipment catalog with specs
3. **equipment_registry** - Installed equipment tracking
4. **orders** - Order management
5. **order_items** - Order line items
6. **shipments** - Delivery tracking
7. **service_regions** - Geographic coverage areas
8. **technicians** - Service personnel
9. **service_appointments** - Scheduling system
10. **warranties** - Warranty tracking
11. **amc_contracts** - Annual Maintenance Contracts
12. **coverage_claims** - Service claims
13. **support_tickets** - Issue tracking
14. **ticket_history** - Ticket updates
15. **invoices** - Billing records
16. **payments** - Payment tracking
17. **parts_catalog** - Spare parts inventory

#### Key Functions:
- `create_database()` - Initialize all tables with proper relationships
- `generate_synthetic_data()` - Create 50 test clients using Faker
- `populate_sample_data()` - Fill tables with realistic medical equipment data
- `execute_query(query, params)` - Safe parameterized query execution
- `get_client_by_credentials(email, client_id)` - Authentication lookup

### Data Population Strategy
- Generate 50 clients across different types (Hospital, Clinic, Laboratory, etc.)
- Create 30+ medical products across 9 categories
- Generate realistic orders, warranties, service appointments
- Create support tickets and invoices for testing

---

## Phase 3: RAG Knowledge Base Setup

### Vector Store Implementation
**File**: `rag_pipeline.py`

#### Documents to Index (10 total):
1. **Returns & Refunds Policy** - 30-day return policy details
2. **Warranty Policy** - Standard 12-month coverage terms
3. **AMC Tiers** - Basic/Standard/Premium service levels
4. **Installation Requirements** - Site preparation guidelines
5. **ISO 13485 Certificate** - Quality management certification
6. **FDA 510(k) Summary** - Regulatory clearance for DiagnosticLab DL-4000
7. **CE Declaration** - European conformity for Surgical Robot SR-2000
8. **Patient Monitor PM-800 Manual** - Operating instructions and specs
9. **Contact Information** - Support hours and regional phone numbers
10. **CT Scanner CT-4000 Specs** - Technical specifications

#### RAG Pipeline Components:
- Text splitter configuration (chunk_size=500, overlap=50)
- OpenAI embeddings integration
- ChromaDB vector store setup
- Similarity search with top-k=3

#### Key Functions:
- `create_knowledge_base()` - Initialize ChromaDB with all documents
- `add_document(title, content)` - Add new documents to vector store
- `search_knowledge(query, k=3)` - Retrieve relevant context

---

## Phase 4: Core Chatbot Logic

### MedEquipChatbot Class
**File**: `chatbot.py`

#### Class Architecture:
```python
class MedEquipChatbot:
    def __init__(self, db_path, vectorstore)
    def authenticate(email, client_id) -> (bool, str)
    def classify_intent(message) -> dict
    def generate_sql(request, client_id) -> str
    def execute_sql_query(query) -> list
    def search_knowledge_base(query) -> str
    def generate_response(message, intent, sql_results, rag_context) -> str
    def chat(message) -> str
```

#### Intent Classification System:
**9 Primary Intents:**
1. ORDER_DELIVERY - Track orders and shipments
2. PRODUCT_INFO - Equipment specs and manuals
3. SERVICE_SCHEDULING - Installation and maintenance
4. WARRANTY_AMC - Coverage verification and upgrades
5. ISSUE_RESOLUTION - Support tickets and troubleshooting
6. FINANCIAL - Invoices and payments
7. SPARE_PARTS - Parts availability and ordering
8. COMPLIANCE - Regulatory documents (FDA, CE, ISO)
9. GENERAL_SUPPORT - Hours, policies, contact info

**Intent Classification Output:**
```json
{
  "primary_intent": "<INTENT_TYPE>",
  "requires_auth": true/false,
  "data_source": "SQL|RAG|BOTH",
  "entities": {
    "order_id": "ORD-2024-1234",
    "serial_number": "US-2022-5678",
    "client_id": "ME-12345",
    "product_model": "MRI-3000",
    "ticket_id": "TKT-2024-0001"
  }
}
```

#### Authentication Flow:
1. Check if intent requires authentication
2. Verify authenticated_client is set
3. If not authenticated, prompt for email + client_id
4. Validate credentials against database
5. Store client context in session

#### Query Routing Logic:
- **SQL Only**: Orders, warranties, invoices, parts inventory
- **RAG Only**: Product manuals, policies, compliance docs
- **BOTH**: Issue resolution (troubleshooting + ticket lookup)

---

## Phase 5: LLM Integration

### System Prompts

#### Master System Prompt:
```
You are an AI-powered customer support assistant for MedEquip Solutions.

Domain: Healthcare/Medical Equipment Manufacturing
Compliance: HIPAA-like confidentiality, no medical advice
Style: Professional, empathetic, concise

Authentication required for:
- Order tracking, warranty checks, invoices, service scheduling
- Verify using email + Client ID (ME-XXXXX)

Current customer: {authenticated_client}
```

#### Intent Classifier Prompt:
```
Analyze user message and classify intent.
Return JSON with: primary_intent, requires_auth, data_source, entities
User message: {message}
```

#### SQL Generator Prompt:
```
Generate SQLite SELECT query for MedEquip database.
Tables: clients, orders, warranties, invoices, support_tickets, etc.
Client filter: {client_id}
Request: {request}
Return ONLY the SQL query.
```

#### Response Generator Prompt:
```
Generate customer support response using:
- User message: {message}
- SQL results: {sql_data}
- Knowledge base: {rag_context}
- Conversation history: {history}

Be professional, reference transaction IDs, offer escalation when needed.
```

### LLM Configuration:
- Model: GPT-4o-mini
- Temperature: 0 (deterministic for support)
- Conversation memory using LangChain message history

---

## Phase 6: Interactive Chat Interface

### CLI Chat Loop
**File**: `chatbot.py`

#### Features:
- Welcome banner with instructions
- Command handling: 'quit', 'auth', 'reset', 'history'
- Authentication workflow
- Conversation context display
- Error handling and graceful fallbacks

#### Sample Flow:
```
==========================================================
MedEquip Solutions Customer Support
Type 'quit' to exit, 'auth' to authenticate
==========================================================

You: What are your support hours?
Assistant: [RAG response with contact info]

You: auth
Email: contact@cityhospital.com
Client ID: ME-10001
System: ✓ Authenticated as City General Hospital

You: When will my order ORD-2024-0001 arrive?
Assistant: [SQL query result with delivery date]
```

---

## Phase 7: Testing & Validation

### Test Scenarios
**File**: `test_scenarios.py`

#### Test Case Coverage:

**UC1: Order Tracking (Auth Required)**
- Input: "When will my order ORD-2024-0001 arrive?"
- Expected: Query orders + shipments, return status and ETA
- Validation: Correct SQL generation, accurate response

**UC2: Product Specs (No Auth)**
- Input: "What are the power requirements for the MRI-3000?"
- Expected: RAG search returns specs from manual
- Validation: Relevant context retrieved, accurate extraction

**UC3: Warranty Check (Auth Required)**
- Input: "Is my ultrasound machine still under warranty? Serial: US-2022-1234"
- Expected: Query warranties + equipment_registry
- Validation: Correct expiration calculation, clear status

**UC4: Support Ticket (Auth Required)**
- Input: "What's the status of ticket TKT-2024-0001?"
- Expected: Query support_tickets + ticket_history
- Validation: Latest status displayed with timeline

**UC5: Compliance Document (No Auth)**
- Input: "I need the FDA 510(k) clearance for the CT-4000"
- Expected: RAG retrieves FDA summary
- Validation: Correct document returned

**UC6: Parts Availability (Auth Required)**
- Input: "Do you have ECG electrodes in stock?"
- Expected: Query parts_inventory
- Validation: Stock quantity and pricing returned

**UC7: Service Scheduling (Auth Required)**
- Input: "URGENT: Our ventilator stopped working, need emergency service"
- Expected: Check service_regions, create priority ticket
- Validation: Escalation triggered, response time communicated

**UC8: Financial Query (Auth Required)**
- Input: "I need a copy of invoice INV-2024-3456"
- Expected: Query invoices table, format invoice details
- Validation: Complete invoice information retrieved

**UC9: General Support (No Auth)**
- Input: "How do I escalate an unresolved issue?"
- Expected: RAG returns escalation policy
- Validation: Clear escalation path provided

---

## Phase 8: Performance Optimization

### Metrics to Track:
| Metric | Target | Measurement |
|--------|--------|-------------|
| Intent Classification Accuracy | 90%+ | Manual review of 100 queries |
| SQL Query Accuracy | 95%+ | Syntax validation + result correctness |
| RAG Answer Precision | 90%+ | Relevance scoring on test set |
| Response Latency | < 2s | Average end-to-end time |
| Authentication Success | 99%+ | Valid credential acceptance |

### Optimization Strategies:
- Cache frequent RAG queries
- Index database for common lookups (order_id, client_id, serial_number)
- Implement query result pagination for large datasets
- Add conversation memory pruning (keep last 10 turns)
- Enable streaming responses for long-form answers

---

## Phase 9: Error Handling & Edge Cases

### Fallback Mechanisms:

**Unknown Intent:**
```
"I'm not sure I understand your request. I can help with:
- Order tracking and delivery
- Product information and manuals
- Service scheduling
- Warranty and AMC inquiries
- Support tickets
- Invoices and payments
- Spare parts
- Compliance documents
Would you like to rephrase your question?"
```

**Authentication Failures:**
- Invalid credentials: Suggest password reset or contact support
- Missing client_id: Guide user to find it on invoice/order confirmation
- Database connection error: Apologize, provide phone support numbers

**SQL Errors:**
- Catch exceptions, log for debugging
- Return generic "Unable to retrieve data" message
- Offer alternative: "Would you like me to connect you with a support agent?"

**RAG Empty Results:**
- "I don't have specific information on that topic"
- Offer to escalate or search more broadly
- Provide general contact information

---

## Phase 10: Deployment Preparation

### Google Colab Notebook Structure:
```markdown
# MedEquip AI Customer Support Chatbot

## Setup
- Install dependencies
- Set OpenAI API key
- Initialize database and RAG

## Database Creation
- Run create_database()
- Generate synthetic data

## Vector Store Setup
- Create ChromaDB
- Index knowledge documents

## Chatbot Initialization
- Instantiate MedEquipChatbot
- Test authentication

## Interactive Chat
- Run chat interface
- Test all 9 use cases

## Performance Metrics
- Display accuracy stats
- Show sample conversations
```

### Configuration File:
**File**: `config.py`

```python
DB_PATH = "data/medequip.db"
VECTORSTORE_PATH = "vectorstore/chroma_db"
OPENAI_MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MAX_HISTORY_TURNS = 10
RAG_TOP_K = 3
SQL_TIMEOUT = 5
```

---

## Phase 11: Documentation

### README.md:
- Project overview and architecture
- Installation instructions
- Usage examples for all 9 use cases
- Authentication flow diagram
- API reference for chatbot methods
- Troubleshooting guide

### Code Documentation:
- Docstrings for all functions and classes
- Inline comments for complex logic
- Type hints for function signatures

---

## Phase 12: Security & Compliance

### Security Measures:
- Parameterized SQL queries (prevent injection)
- Client_id filtering on all authenticated queries
- No PHI storage or logging
- Rate limiting considerations

### HIPAA-like Guidelines:
- No medical advice in responses
- No diagnosis or treatment recommendations
- Redirect clinical questions to healthcare professionals
- Maintain confidentiality of customer data

---

## Implementation Checklist

### Database Layer:
- [ ] Create all 17 tables with proper schema
- [ ] Implement foreign key relationships
- [ ] Generate 50 synthetic clients
- [ ] Populate products, orders, warranties, tickets
- [ ] Create authentication lookup function
- [ ] Test SQL query execution

### RAG Pipeline:
- [ ] Initialize ChromaDB vector store
- [ ] Index all 10 knowledge documents
- [ ] Configure text splitter (chunk_size=500)
- [ ] Implement similarity search
- [ ] Test retrieval accuracy

### Chatbot Core:
- [ ] Build MedEquipChatbot class structure
- [ ] Implement intent classification
- [ ] Create SQL query generator
- [ ] Build response generator
- [ ] Add authentication workflow
- [ ] Implement conversation memory

### LLM Integration:
- [ ] Configure OpenAI client
- [ ] Write system prompts (master, intent, SQL, response)
- [ ] Test intent classification accuracy
- [ ] Validate SQL generation
- [ ] Optimize response quality

### Interface:
- [ ] Build interactive CLI chat loop
- [ ] Add command handling (quit, auth, reset)
- [ ] Implement error messages
- [ ] Create welcome banner

### Testing:
- [ ] Test all 9 use cases
- [ ] Validate authentication flow
- [ ] Check SQL query accuracy
- [ ] Verify RAG retrieval precision
- [ ] Measure response latency
- [ ] Test edge cases and errors

### Documentation:
- [ ] Write comprehensive README
- [ ] Add code docstrings
- [ ] Create usage examples
- [ ] Document configuration options

### Optimization:
- [ ] Add database indexes
- [ ] Implement query caching
- [ ] Optimize vector search
- [ ] Reduce response latency

---

## Success Criteria

### Functional Requirements:
✓ Correctly classifies 9 different intent types  
✓ Authenticates users with email + client_id  
✓ Generates accurate SQL queries for structured data  
✓ Retrieves relevant context from RAG for unstructured data  
✓ Maintains conversation context across multiple turns  
✓ Provides helpful responses with reference numbers  
✓ Handles errors gracefully with fallback messages  

### Performance Requirements:
✓ 90%+ intent classification accuracy  
✓ 95%+ SQL query correctness  
✓ 90%+ RAG answer precision  
✓ < 2 second average response time  
✓ 99%+ authentication success rate  

### Compliance Requirements:
✓ No PHI disclosure  
✓ No medical advice provided  
✓ Parameterized queries prevent SQL injection  
✓ Client data isolated by authenticated client_id  

---

## Next Steps After Implementation

1. **Enhanced Features:**
   - Multi-language support
   - Sentiment analysis for ticket prioritization
   - Proactive notifications (warranty expiring, PM due)
   - Integration with CRM system

2. **Analytics Dashboard:**
   - Track conversation metrics
   - Monitor intent distribution
   - Identify common customer issues
   - Measure resolution rates

3. **Model Fine-tuning:**
   - Collect conversation logs
   - Fine-tune on domain-specific data
   - Improve intent classification
   - Optimize SQL generation

4. **Production Deployment:**
   - Migrate from SQLite to PostgreSQL
   - Deploy on cloud infrastructure
   - Add API endpoints for web/mobile apps
   - Implement logging and monitoring

---

## Resources & References

- **LangChain Docs**: https://python.langchain.com/docs/
- **ChromaDB Guide**: https://docs.trychroma.com/
- **OpenAI API**: https://platform.openai.com/docs/
- **SQLite Schema Design**: https://www.sqlite.org/schematab.html
- **Faker Library**: https://faker.readthedocs.io/

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Setup | 30 min | None |
| Phase 2: Database | 2 hours | Phase 1 |
| Phase 3: RAG Pipeline | 1.5 hours | Phase 1 |
| Phase 4: Chatbot Core | 3 hours | Phases 2, 3 |
| Phase 5: LLM Integration | 2 hours | Phase 4 |
| Phase 6: Interface | 1 hour | Phase 5 |
| Phase 7: Testing | 2 hours | Phase 6 |
| Phase 8: Optimization | 1.5 hours | Phase 7 |
| Phase 9: Error Handling | 1 hour | Phase 8 |
| Phase 10: Deployment Prep | 1 hour | Phase 9 |
| Phase 11: Documentation | 1.5 hours | All phases |
| Phase 12: Security Review | 1 hour | All phases |

**Total Estimated Time: 18 hours**

---

*This plan provides a complete roadmap for implementing the MedEquip AI Chatbot. Each phase builds on previous work and includes specific deliverables and validation criteria.*
