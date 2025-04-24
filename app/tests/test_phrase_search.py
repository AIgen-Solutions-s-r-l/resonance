import pytest
from app.libs.job_matcher.query_builder import QueryBuilder
from sqlalchemy import text

# Mock session and query object for testing purposes
class MockSession:
    def query(self, *args, **kwargs):
        return MockQuery()

class MockQuery:
    def filter(self, *args, **kwargs):
        return self
    
    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def params(self, *args, **kwargs):
        # This is where we'll capture the parameters
        self._params = args[0]
        return self

    def statement(self):
        # This is where we'll capture the generated SQL statement
        # In a real scenario, this would be a SQLAlchemy Select object
        # For this mock, we'll just return a placeholder or capture the filter/where calls
        # A more sophisticated mock might build a simplified SQL string
        # For now, let's assume the QueryBuilder returns a text() object or similar
        # We need to inspect the QueryBuilder's output directly if it doesn't return a query object
        # Let's adjust the test approach based on how QueryBuilder is used and what it returns.

        # Re-evaluating: The QueryBuilder modifies an existing query object.
        # We need to mock the query object to capture the filter/where calls and their arguments.
        pass # The actual assertion will inspect the mock object after QueryBuilder methods are called

# Let's refine the MockQuery to capture filter/where calls
class CapturingMockQuery:
    def __init__(self):
        self._filters = []
        self._wheres = []
        self._params = {}
        self._order_by = []
        self._limit = None
        self._offset = None

    def filter(self, *args, **kwargs):
        self._filters.append((args, kwargs))
        return self
    
    def where(self, *args, **kwargs):
        self._wheres.append((args, kwargs))
        return self

    def order_by(self, *args, **kwargs):
        self._order_by.append((args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self._limit = args[0] if args else None
        return self

    def offset(self, *args, **kwargs):
        self._offset = args[0] if args else None
        return self

    def params(self, *args, **kwargs):
        self._params.update(args[0]) # Assuming params are passed as a dict
        return self

    def statement(self):
        # This mock doesn't build a full statement, but we can inspect the captured calls
        raise NotImplementedError("MockQuery does not build a full statement")

    def get_filters(self):
        return self._filters

    def get_wheres(self):
        return self._wheres
    
    def get_params(self):
        return self._params

# Assuming QueryBuilder takes a query object and modifies it
# We'll need a mock for the 'Job' model or whatever the query is built upon
class MockJobModel:
    # Define attributes that QueryBuilder might access, e.g., columns
    # For keyword search, it likely uses a text column, let's call it 'description'
    description = text("description") # Mock a column access

# Now, let's write the test cases using the refined mock

@pytest.fixture
def query_builder():
    # QueryBuilder likely needs a session and potentially other dependencies
    # Based on app/libs/job_matcher/query_builder.py, it takes a session and a model
    mock_session = MockSession() # We don't use the session mock directly in this test approach, but QueryBuilder might expect it
    return QueryBuilder(mock_session, MockJobModel)

def test_single_word_keyword_search(query_builder):
    mock_query = CapturingMockQuery()
    keywords = ["business"]
    
    # Call the method that builds keyword filters
    # Assuming QueryBuilder has a public method or we can test the internal logic via a helper
    # Let's assume _build_keyword_filters is the relevant internal method we want to test indirectly
    # Or, QueryBuilder's main build method calls _build_keyword_filters
    # Let's test the public method that incorporates keyword filtering.
    # Based on app/libs/job_matcher/query_builder.py, the method is likely part of the build process.
    # Let's assume there's a method like `build_query_with_filters` that takes keywords.
    # If not, we might need to mock more or test the internal method directly if possible.

    # Looking at app/libs/job_matcher/query_builder.py, the main method is `build_query`.
    # It takes various filter parameters, including `keywords`.
    # Let's test `build_query` and inspect the resulting mock query.

    # Reset the mock_query for each test
    mock_query = CapturingMockQuery()
    
    # QueryBuilder's build_query method takes a base query and filters
    # Let's assume build_query is structured like: build_query(base_query, filters)
    # And filters is a dict including 'keywords'
    
    # Re-reading the task: "Reference the existing implementation in app/libs/job_matcher/query_builder.py where we've updated the _build_keyword_filters method"
    # This suggests we should focus on testing the logic within or called by _build_keyword_filters.
    # It might be easier to test the _build_keyword_filters method directly if it's accessible or can be isolated.
    # If not, testing the public method that uses it (like build_query) is the way.

    # Let's assume QueryBuilder has a method `apply_keyword_filters` that takes the query and keywords.
    # If not, we'll adjust after reading the actual QueryBuilder code.

    # Let's try testing the `build_query` method and see what it does to the mock.
    # We need to provide other required parameters to `build_query` if any.
    # Based on the file structure, QueryBuilder is used in `app/libs/job_matcher/matcher.py`.
    # Let's look at how it's instantiated and used there (mentally or by reading the file if needed).
    # It seems `build_query` takes `base_query`, `filters`, `limit`, `offset`, `order_by`.
    # We only care about the `filters` part for this test.

    mock_query = CapturingMockQuery()
    filters = {"keywords": keywords}
    
    # QueryBuilder needs a base query to start with. Let's provide our mock.
    # The QueryBuilder constructor takes session and model.
    # The build_query method takes the base query.
    
    # Let's create a QueryBuilder instance
    qb = QueryBuilder(MockSession(), MockJobModel)
    
    # Call build_query with our mock query and filters
    built_query = qb.build_query(
        base_query=mock_query,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None
    )

    # Now, inspect the mock_query (which is the same object as built_query)
    # We expect one filter/where call for a single keyword, using ILIKE.
    captured_wheres = built_query.get_wheres()
    captured_params = built_query.get_params()

    assert len(captured_wheres) > 0, "Expected at least one WHERE clause for keywords"
    
    # Check the first WHERE clause (assuming keywords are processed first)
    # The exact structure depends on the QueryBuilder implementation
    # It might be something like: JobModel.description.ilike(...)
    # Or text("description ILIKE :keyword_0")
    
    # Let's assume it generates a text() clause like "description ILIKE :keyword_0"
    # and adds parameters like {'keyword_0': '%business%'}
    
    # We need to check the string representation of the clause and the parameters.
    # The captured_wheres list contains tuples: (args, kwargs)
    # The first element of the first tuple should be the clause.
    
    # Let's assume the clause is a text() object or similar that can be converted to string
    # and the parameters are in the captured_params dict.

    # Example assertion structure (will need adjustment based on actual QueryBuilder output):
    # assert "description ILIKE :keyword_0" in str(captured_wheres[0][0][0])
    # assert captured_params.get('keyword_0') == '%business%'

    # Let's refine the assertion based on the likely structure:
    # It's likely building conditions like `JobModel.description.ilike(...)`
    # We need to check the method call on the mock column object.
    # Let's update MockJobModel and CapturingMockQuery to capture method calls on columns.

class MockColumn:
    def __init__(self, name):
        self.name = name
        self._method_calls = []

    def ilike(self, *args, **kwargs):
        self._method_calls.append(('ilike', args, kwargs))
        return text(f"{self.name} ILIKE :param") # Return a text object for the clause representation

    def __eq__(self, other):
         # Needed for comparisons in filter/where calls if QueryBuilder does `column == value`
         self._method_calls.append(('eq', (other,), {}))
         return text(f"{self.name} = :param")

    def get_method_calls(self):
        return self._method_calls

class MockJobModelRefined:
    def __init__(self):
        self.description = MockColumn("description")
        # Add other columns if needed by QueryBuilder

class CapturingMockQueryRefined:
    def __init__(self):
        self._filters = []
        self._wheres = []
        self._params = {}
        self._order_by = []
        self._limit = None
        self._offset = None

    def filter(self, *args, **kwargs):
        self._filters.append((args, kwargs))
        return self
    
    def where(self, *args, **kwargs):
        self._wheres.append((args, kwargs))
        return self

    def order_by(self, *args, **kwargs):
        self._order_by.append((args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self._limit = args[0] if args else None
        return self

    def offset(self, *args, **kwargs):
        self._offset = args[0] if args else None
        return self

    def params(self, *args, **kwargs):
        self._params.update(args[0]) # Assuming params are passed as a dict
        return self

    def get_filters(self):
        return self._filters

    def get_wheres(self):
        return self._wheres
    
    def get_params(self):
        return self._params

# Update the fixture to use the refined mock model
@pytest.fixture
def query_builder_refined():
    mock_session = MockSession()
    return QueryBuilder(mock_session, MockJobModelRefined())

# Rewrite the first test with refined mocks
def test_single_word_keyword_search_refined(query_builder_refined):
    mock_query = CapturingMockQueryRefined()
    keywords = ["business"]
    filters = {"keywords": keywords}
    
    built_query = query_builder_refined.build_query(
        base_query=mock_query,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None
    )

    captured_wheres = built_query.get_wheres()
    captured_params = built_query.get_params()

    # Expect one WHERE clause for the single keyword
    assert len(captured_wheres) == 1
    
    # The WHERE clause should be the result of a method call on the description column
    # Let's inspect the arguments passed to the where() call on the mock query
    where_args, where_kwargs = captured_wheres[0]
    
    # The first argument should be the clause generated by MockColumn.ilike()
    clause = where_args[0]
    
    # Check that the clause is a text object representing the ILIKE condition
    assert isinstance(clause, text)
    assert "description ILIKE" in str(clause)

    # Check the parameters added
    # The parameter name will be generated by QueryBuilder, likely based on the keyword index
    # e.g., 'keyword_0'
    assert len(captured_params) == 1
    param_key = list(captured_params.keys())[0]
    assert captured_params[param_key] == '%business%'

    # We can also check the method calls on the mock column object if needed,
    # but checking the resulting clause and parameters on the query mock is sufficient
    # to verify the output of _build_keyword_filters logic.


def test_multi_word_phrase_search(query_builder_refined):
    mock_query = CapturingMockQueryRefined()
    keywords = ["business account manager"]
    filters = {"keywords": keywords}
    
    built_query = query_builder_refined.build_query(
        base_query=mock_query,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None
    )

    captured_wheres = built_query.get_wheres()
    captured_params = built_query.get_params()

    # Expect one WHERE clause for the phrase
    assert len(captured_wheres) == 1
    
    where_args, where_kwargs = captured_wheres[0]
    clause = where_args[0]
    
    assert isinstance(clause, text)
    # The clause should contain the exact phrase search logic, likely using LIKE or ILIKE with underscores
    # e.g., "description ILIKE :phrase_0" with param '%business_account_manager%'
    # Or it might use a full-text search function depending on the DB/implementation
    # Based on the prompt mentioning preserving the complete phrase and ILIKE,
    # it's likely using ILIKE with underscores or similar.
    # Let's assume it uses ILIKE with underscores for spaces.

    assert "description ILIKE" in str(clause)

    assert len(captured_params) == 1
    param_key = list(captured_params.keys())[0]
    # The parameter should be the phrase with spaces replaced by underscores and wrapped in %
    assert captured_params[param_key] == '%business_account_manager%'


def test_multiple_individual_words_as_potential_phrase(query_builder_refined):
    mock_query = CapturingMockQueryRefined()
    keywords = ["business", "account", "manager"]
    filters = {"keywords": keywords}
    
    built_query = query_builder_refined.build_query(
        base_query=mock_query,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None
    )

    captured_wheres = built_query.get_wheres()
    captured_params = built_query.get_params()

    # Expect multiple WHERE clauses or a single complex WHERE clause
    # The prompt says "includes both the combined phrase AND individual words"
    # This suggests a structure like (phrase_condition OR word1_condition OR word2_condition OR word3_condition)
    # Or potentially separate WHERE clauses combined by AND by SQLAlchemy's filter/where calls.
    # Let's assume it generates a single WHERE clause with OR conditions.

    assert len(captured_wheres) == 1 # Assuming a single combined clause
    
    where_args, where_kwargs = captured_wheres[0]
    clause = where_args[0]
    
    assert isinstance(clause, text)
    
    # Check for the presence of both phrase and individual word conditions in the clause string
    # The exact string will depend on how QueryBuilder constructs the OR conditions.
    # It might look like: "(description ILIKE :phrase_0 OR description ILIKE :keyword_0 OR description ILIKE :keyword_1 OR description ILIKE :keyword_2)"
    
    clause_str = str(clause)
    assert "description ILIKE :phrase_0" in clause_str
    assert "description ILIKE :keyword_0" in clause_str
    assert "description ILIKE :keyword_1" in clause_str
    assert "description ILIKE :keyword_2" in clause_str
    assert " OR " in clause_str # Should be combined with OR

    # Check the parameters
    # Expect parameters for the phrase and each individual word
    assert len(captured_params) == 4
    assert captured_params.get('phrase_0') == '%business_account_manager%'
    assert captured_params.get('keyword_0') == '%business%'
    assert captured_params.get('keyword_1') == '%account%'
    assert captured_params.get('keyword_2') == '%manager%'