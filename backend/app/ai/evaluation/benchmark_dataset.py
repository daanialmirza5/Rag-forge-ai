"""Standard Multi-Domain Benchmark Dataset for RAG Retrieval & Reranking Evaluation.

Contains structured queries, reference documents, and graded relevance assessments across:
- Distributed Systems & Cloud Architecture
- Financial Regulations & 10-K Analysis
- Medical / Clinical Practice Guidelines
- Cyber Security & Compliance (SOC2 / GDPR)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DocumentChunk:
    id: str
    content: str
    domain: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class BenchmarkItem:
    query_id: str
    query: str
    domain: str
    ground_truth_relevance: Dict[str, float]  # doc_id -> relevance score (0.0 to 3.0 scale)
    description: Optional[str] = None


@dataclass
class BenchmarkDataset:
    name: str
    version: str
    documents: List[DocumentChunk]
    items: List[BenchmarkItem]

    def get_document_by_id(self, doc_id: str) -> Optional[DocumentChunk]:
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None

    def get_all_doc_ids(self) -> List[str]:
        return [doc.id for doc in self.documents]


def get_standard_rag_benchmark() -> BenchmarkDataset:
    """Returns a curated 20-chunk, 6-query multi-domain evaluation benchmark with gold-standard relevance."""
    documents = [
        # Distributed Systems (DOC-DIST-01 to DOC-DIST-05)
        DocumentChunk(
            id="DOC-DIST-01",
            content="Raft is a consensus algorithm for managing a replicated log. It produces a result equivalent to Paxos, and it is as efficient as Paxos, but its structure is different: Raft separates key elements of consensus, such as leader election, log replication, and safety.",
            domain="distributed_systems",
            metadata={"source": "raft-paper", "topic": "consensus"},
        ),
        DocumentChunk(
            id="DOC-DIST-02",
            content="In Raft consensus, if a follower receives a RequestVote RPC with a term less than its currentTerm, the follower rejects the vote immediately (reply false). Followers only vote for candidates with up-to-date logs.",
            domain="distributed_systems",
            metadata={"source": "raft-paper", "topic": "leader-election"},
        ),
        DocumentChunk(
            id="DOC-DIST-03",
            content="Vector clocks and Lamport timestamps determine the partial ordering of events in distributed systems without requiring synchronized physical wall clocks. They resolve causality violations across network partitions.",
            domain="distributed_systems",
            metadata={"source": "dist-systems-guide", "topic": "clocks"},
        ),
        DocumentChunk(
            id="DOC-DIST-04",
            content="Consistent hashing with virtual nodes maps keys and nodes to a hash ring, reducing keys that need relocation when cluster nodes join or leave from K/N to K/N on average.",
            domain="distributed_systems",
            metadata={"source": "dynamo-paper", "topic": "partitioning"},
        ),
        DocumentChunk(
            id="DOC-DIST-05",
            content="Two-phase locking (2PL) guarantees serializability in distributed database transactions by acquiring shared and exclusive locks before releasing any locks, preventing cascading aborts.",
            domain="distributed_systems",
            metadata={"source": "db-internals", "topic": "transactions"},
        ),

        # Financial Regulations (DOC-FIN-01 to DOC-FIN-05)
        DocumentChunk(
            id="DOC-FIN-01",
            content="Under ASC 606 and IFRS 15, revenue recognition requires a 5-step model: 1. Identify the contract; 2. Identify performance obligations; 3. Determine transaction price; 4. Allocate transaction price; 5. Recognize revenue when obligations are satisfied.",
            domain="finance",
            metadata={"standard": "ASC 606", "topic": "revenue"},
        ),
        DocumentChunk(
            id="DOC-FIN-02",
            content="Adjusted EBITDA excludes non-recurring restructuring expenses, stock-based compensation, impairment of goodwill, and unrealized foreign exchange gains or losses from standard GAAP operating income.",
            domain="finance",
            metadata={"standard": "GAAP", "topic": "ebitda"},
        ),
        DocumentChunk(
            id="DOC-FIN-03",
            content="Working capital is calculated as current assets minus current liabilities. A current ratio above 1.5 indicates healthy short-term solvency and operational liquidity.",
            domain="finance",
            metadata={"standard": "analysis", "topic": "liquidity"},
        ),
        DocumentChunk(
            id="DOC-FIN-04",
            content="Capitalized software development costs under ASC 350-40 must occur during the application development stage and amortize over the estimated useful life on a straight-line basis.",
            domain="finance",
            metadata={"standard": "ASC 350", "topic": "capitalization"},
        ),
        DocumentChunk(
            id="DOC-FIN-05",
            content="Debt covenants specify minimum interest coverage ratios (EBIT / Interest Expense) that the borrower must maintain to avoid technical loan default.",
            domain="finance",
            metadata={"standard": "credit", "topic": "covenants"},
        ),

        # Compliance & Security (DOC-SEC-01 to DOC-SEC-05)
        DocumentChunk(
            id="DOC-SEC-01",
            content="SOC 2 Type II audits examine both the design suitability and operational effectiveness of trust services criteria controls (Security, Availability, Confidentiality) over a minimum observation period of 6 months.",
            domain="security",
            metadata={"compliance": "SOC2", "topic": "audit"},
        ),
        DocumentChunk(
            id="DOC-SEC-02",
            content="GDPR Article 17 (Right to Erasure) mandates that data controllers erase personal data without undue delay when the data is no longer necessary or the data subject withdraws consent.",
            domain="security",
            metadata={"compliance": "GDPR", "topic": "erasure"},
        ),
        DocumentChunk(
            id="DOC-SEC-03",
            content="Zero Trust Network Architecture (ZTNA) adheres to the principle of least privilege, requiring continuous explicit authentication and cryptographic authorization for every transaction regardless of network perimeter location.",
            domain="security",
            metadata={"compliance": "NIST", "topic": "zero-trust"},
        ),
        DocumentChunk(
            id="DOC-SEC-04",
            content="AES-256-GCM provides both confidentiality and authenticated data integrity verification, mitigating ciphertext tampering attacks through a Galois field authentication tag.",
            domain="security",
            metadata={"compliance": "crypto", "topic": "encryption"},
        ),
        DocumentChunk(
            id="DOC-SEC-05",
            content="Role-Based Access Control (RBAC) assigns permissions to specific organizational roles rather than individual users, simplifying tenant isolation and access governance.",
            domain="security",
            metadata={"compliance": "access", "topic": "rbac"},
        ),

        # Clinical Guidelines (DOC-MED-01 to DOC-MED-05)
        DocumentChunk(
            id="DOC-MED-01",
            content="First-line pharmacotherapy for primary hypertension in non-black adult patients includes ACE inhibitors, ARBs, dihydropyridine calcium channel blockers, or thiazide diuretics.",
            domain="clinical",
            metadata={"guideline": "AHA/ACC", "topic": "hypertension"},
        ),
        DocumentChunk(
            id="DOC-MED-02",
            content="In suspected sepsis, serum lactate measurement, blood culture collection prior to broad-spectrum antimicrobial administration, and 30 mL/kg crystalloid fluid resuscitation must be completed within the 1-hour bundle.",
            domain="clinical",
            metadata={"guideline": "Surviving Sepsis", "topic": "sepsis"},
        ),
        DocumentChunk(
            id="DOC-MED-03",
            content="Type 2 diabetes glycemic control target is generally an HbA1c < 7.0% for non-pregnant adults, with metformin remaining the first-line oral antihyperglycemic medication unless contraindicated by eGFR < 30 mL/min.",
            domain="clinical",
            metadata={"guideline": "ADA", "topic": "diabetes"},
        ),
        DocumentChunk(
            id="DOC-MED-04",
            content="Community-acquired pneumonia (CAP) outpatient treatment in patients without comorbidities includes amoxicillin 1g TID or doxycycline 100mg BID as first-line empiric monotherapy.",
            domain="clinical",
            metadata={"guideline": "ATS/IDSA", "topic": "pneumonia"},
        ),
        DocumentChunk(
            id="DOC-MED-05",
            content="Acute ischemic stroke management requires administration of IV alteplase (0.9 mg/kg) within 4.5 hours of symptom onset after non-contrast head CT excludes intracranial hemorrhage.",
            domain="clinical",
            metadata={"guideline": "AHA/ASA", "topic": "stroke"},
        ),
    ]

    items = [
        BenchmarkItem(
            query_id="Q-DIST-01",
            query="How does the Raft consensus algorithm elect a leader and maintain log safety?",
            domain="distributed_systems",
            ground_truth_relevance={
                "DOC-DIST-01": 3.0,  # Highly relevant primary definition
                "DOC-DIST-02": 3.0,  # Highly relevant vote & term safety logic
                "DOC-DIST-03": 0.0,  # Clocks (irrelevant)
                "DOC-DIST-04": 0.0,  # Consistent hashing (irrelevant)
                "DOC-DIST-05": 1.0,  # Locking/transactions (marginally related)
            },
            description="Tests multi-document consensus retrieval with strict topical precision.",
        ),
        BenchmarkItem(
            query_id="Q-FIN-01",
            query="What are the 5 steps for revenue recognition under ASC 606 and how is Adjusted EBITDA calculated?",
            domain="finance",
            ground_truth_relevance={
                "DOC-FIN-01": 3.0,  # Core ASC 606 5-step model
                "DOC-FIN-02": 3.0,  # Core Adjusted EBITDA exclusions
                "DOC-FIN-03": 1.0,  # Working capital / liquidity
                "DOC-FIN-04": 1.0,  # Software capitalization
                "DOC-FIN-05": 0.0,  # Debt covenants
            },
            description="Tests multi-intent financial query requiring hybrid dense and exact lexical matching.",
        ),
        BenchmarkItem(
            query_id="Q-SEC-01",
            query="What is the observation period for SOC 2 Type II reports and what are data deletion requirements under GDPR Article 17?",
            domain="security",
            ground_truth_relevance={
                "DOC-SEC-01": 3.0,  # SOC 2 Type II 6-month observation period
                "DOC-SEC-02": 3.0,  # GDPR Article 17 Right to Erasure
                "DOC-SEC-03": 1.0,  # Zero trust security
                "DOC-SEC-04": 0.0,  # AES crypto
                "DOC-SEC-05": 0.0,  # RBAC
            },
            description="Tests exact regulatory article code and compliance standard retrieval.",
        ),
        BenchmarkItem(
            query_id="Q-MED-01",
            query="What is the 1-hour resuscitation bundle for suspected sepsis and first line treatment for hypertension?",
            domain="clinical",
            ground_truth_relevance={
                "DOC-MED-01": 3.0,  # First-line hypertension pharmacotherapy
                "DOC-MED-02": 3.0,  # Sepsis 1-hour bundle (lactate, fluids, antibiotics)
                "DOC-MED-03": 0.5,  # Diabetes
                "DOC-MED-04": 0.5,  # Pneumonia
                "DOC-MED-05": 0.0,  # Stroke
            },
            description="Tests clinical guideline retrieval across acute emergency and chronic care protocols.",
        ),
        BenchmarkItem(
            query_id="Q-DIST-02",
            query="How do consistent hashing and virtual nodes handle cluster node failures and key relocation?",
            domain="distributed_systems",
            ground_truth_relevance={
                "DOC-DIST-04": 3.0,  # Consistent hashing and virtual nodes
                "DOC-DIST-03": 1.0,  # Vector clocks
                "DOC-DIST-01": 0.0,  # Raft
                "DOC-DIST-05": 0.0,  # 2PL
            },
            description="Tests precise keyword and architectural retrieval in distributed storage.",
        ),
        BenchmarkItem(
            query_id="Q-SEC-02",
            query="What cryptographic algorithm provides authenticated encryption with Galois field verification?",
            domain="security",
            ground_truth_relevance={
                "DOC-SEC-04": 3.0,  # AES-256-GCM Galois field authenticated encryption
                "DOC-SEC-03": 1.0,  # Zero trust
                "DOC-SEC-01": 0.0,  # SOC2
                "DOC-SEC-05": 0.0,  # RBAC
            },
            description="Tests fine-grained technical cryptographic concept retrieval.",
        ),
    ]

    return BenchmarkDataset(
        name="RAG-Forge Multi-Domain Enterprise IR Benchmark",
        version="1.0.0",
        documents=documents,
        items=items,
    )
