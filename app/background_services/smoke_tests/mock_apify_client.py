import time
import json
import os
import random
import copy

# Configuration constants
LEADS_PER_DATASET_CALL = 10  # Number of leads returned per dataset call

# Path to the original dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset_apollo-io-scraper_2025-05-21_19-33-02-963.json')

# Global dataset cache and in-memory tracking
_FULL_DATASET = None
_DATASET_LOADED = False
_CONSUMED_INDICES = set()  # In-memory tracking of consumed indices

def load_original_dataset():
    """Load the original dataset from file once at startup."""
    global _FULL_DATASET, _DATASET_LOADED
    
    if not _DATASET_LOADED:
        print(f"[MockApifyClient] Loading original dataset from: {DATASET_PATH}")
        try:
            with open(DATASET_PATH, 'r') as f:
                _FULL_DATASET = json.load(f)
            _DATASET_LOADED = True
            
            # Debug: Check the structure and content
            print(f"[MockApifyClient] Successfully loaded {len(_FULL_DATASET)} total records from file")
            
            # Check first few records for structure
            if _FULL_DATASET and len(_FULL_DATASET) > 0:
                first_record = _FULL_DATASET[0]
                print(f"[MockApifyClient] Sample record keys: {list(first_record.keys())}")
                print(f"[MockApifyClient] Sample email: {first_record.get('email', 'NO_EMAIL_FIELD')}")
            else:
                print(f"[MockApifyClient] WARNING: Dataset appears to be empty!")
                
        except Exception as e:
            print(f"[MockApifyClient] ERROR loading dataset: {e}")
            _FULL_DATASET = []
            _DATASET_LOADED = True
    
    return _FULL_DATASET

def get_consumed_indices():
    """Get the list of already consumed indices from memory."""
    return _CONSUMED_INDICES.copy()

def mark_indices_consumed(indices):
    """Mark indices as consumed in memory."""
    global _CONSUMED_INDICES
    
    # Add new indices to the in-memory set
    _CONSUMED_INDICES.update(indices)
    
    print(f"[MockApifyClient] Marked indices {indices} as consumed. Total consumed: {len(_CONSUMED_INDICES)}")

def get_next_available_indices(count=LEADS_PER_DATASET_CALL):
    """Get the next available indices that haven't been consumed yet."""
    dataset = load_original_dataset()
    consumed = get_consumed_indices()
    
    print(f"[MockApifyClient] Looking for {count} available indices")
    print(f"[MockApifyClient] Dataset size: {len(dataset)}")
    print(f"[MockApifyClient] Already consumed: {len(consumed)} indices")
    print(f"[MockApifyClient] Consumed indices: {sorted(list(consumed)) if len(consumed) < 20 else f'{len(consumed)} indices (showing first 10): {sorted(list(consumed))[:10]}'}")
    
    available_indices = []
    for i in range(len(dataset)):
        if i not in consumed:
            available_indices.append(i)
            if len(available_indices) >= count:
                break
    
    print(f"[MockApifyClient] Found {len(available_indices)} available indices out of {count} requested")
    print(f"[MockApifyClient] Available indices: {available_indices}")
    print(f"[MockApifyClient] Total consumed so far: {len(consumed)}/{len(dataset)}")
    
    return available_indices

def get_next_campaign_data(leads_count=LEADS_PER_DATASET_CALL):
    """Get the next available slice of leads using in-memory indexed data."""
    dataset = load_original_dataset()
    
    # Get next available indices
    indices = get_next_available_indices(leads_count)
    
    if not indices:
        print(f"[MockApifyClient] WARNING: No more available data! All {len(dataset)} records consumed.")
        return []
    
    # Mark these indices as consumed in memory
    mark_indices_consumed(indices)
    
    # Get the actual data (deep copy to avoid modifying original)
    campaign_data = [copy.deepcopy(dataset[i]) for i in indices]
    
    # Log the emails being provided for debugging
    emails_provided = [lead.get('email') for lead in campaign_data]
    valid_emails = [email for email in emails_provided if email and email.strip()]
    
    print(f"[MockApifyClient] Provided {len(campaign_data)} leads using indices {indices}")
    print(f"[MockApifyClient] Emails provided: {emails_provided}")
    print(f"[MockApifyClient] Valid emails: {len(valid_emails)}/{len(emails_provided)}")
    
    # Debug: show sample data structure
    if campaign_data:
        sample_lead = campaign_data[0]
        print(f"[MockApifyClient] Sample lead structure: {list(sample_lead.keys())}")
    
    return campaign_data

def reset_dataset():
    """Reset dataset consumption tracking in memory for test isolation."""
    global _CONSUMED_INDICES
    
    _CONSUMED_INDICES = set()
    print(f"[MockApifyClient] Reset in-memory dataset consumption tracking")

def get_dataset_status():
    """Get current dataset status for debugging."""
    dataset = load_original_dataset()
    consumed = get_consumed_indices()
    return {
        "status": "loaded",
        "total": len(dataset),
        "consumed": len(consumed),
        "remaining": len(dataset) - len(consumed)
    }

class MockActor:
    def __init__(self, actor_id):
        self.actor_id = actor_id

    def call(self, run_input=None):
        # Simulate async process
        time.sleep(random.uniform(0.1, 0.3))
        
        # Return a mock dataset ID
        dataset_id = f"mock_dataset_{random.randint(1000, 9999)}"
        return {"defaultDatasetId": dataset_id}

class MockDataset:
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
        print(f"[MockDataset] Created dataset {dataset_id}")
    
    def iterate_items(self):
        """Get next available data slice from in-memory dataset."""
        print(f"[MockDataset] Getting next data slice for dataset {self.dataset_id}")
        
        # Get next available data using the configured constant
        campaign_data = get_next_campaign_data(LEADS_PER_DATASET_CALL)
        
        print(f"[MockDataset] Returning {len(campaign_data)} leads for dataset {self.dataset_id}")
        
        return iter(campaign_data)

class MockApifyClient:
    def __init__(self, api_token=None):
        self.api_token = api_token
        self.actor_id = "mock/apollo-io-scraper"  # Mock actor ID
        print(f"[MockApifyClient] Initialized with api_token={'*' * 5 if api_token else None}")
        print(f"[MockApifyClient] Using mock actor_id: {self.actor_id}")
        # Load the dataset once when the client is instantiated
        load_original_dataset()
    
    def actor(self, actor_id):
        return MockActor(actor_id)

    def dataset(self, dataset_id):
        print(f"[MockApifyClient] Creating dataset {dataset_id}")
        return MockDataset(dataset_id)

def reset_campaign_counter():
    """Reset for test isolation - resets the in-memory dataset tracking."""
    reset_dataset()
    print(f"[MockApifyClient] System reset for new test run")

def get_mock_leads_data():
    """Get mock leads data from in-memory dataset."""
    return get_next_campaign_data(LEADS_PER_DATASET_CALL)

__all__ = ["MockApifyClient", "get_mock_leads_data", "reset_campaign_counter", "get_next_campaign_data", "reset_dataset", "get_dataset_status"] 