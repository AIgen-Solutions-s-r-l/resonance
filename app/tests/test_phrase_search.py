import pytest
from app.libs.job_matcher.query_builder import JobQueryBuilder
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
        # For now, let's assume the JobQueryBuilder returns a text() object or similar
        # We need to inspect the JobQueryBuilder's output directly if it doesn't return a query object
        # Let's adjust the test approach based on how JobQueryBuilder is used and what it returns.

        # Re-evaluating: The JobQueryBuilder modifies an existing query object.
        # We need to mock the query object to capture the filter/where calls and their arguments.
        pass # The actual assertion will inspect the mock object after JobQueryBuilder methods are called

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

# Assuming JobQueryBuilder takes a query object and modifies it
# We'll need a mock for the 'Job' model or whatever the query is built upon
class MockJobModel:
    # Define attributes that JobQueryBuilder might access, e.g., columns
    # For keyword search, it likely uses a text column, let's call it 'description'
    description = text("description") # Mock a column access

# Now, let's write the test cases using the refined mock

# The JobQueryBuilder is a singleton, so we import the instance directly
from app.libs.job_matcher.query_builder import query_builder as job_query_builder

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
        # For now, let's assume the JobQueryBuilder returns a text() object or similar
        # We need to inspect the JobQueryBuilder's output directly if it doesn't return a query object
        # Let's adjust the test approach based on how JobQueryBuilder is used and what it returns.

        # Re-evaluating: The JobQueryBuilder modifies an existing query object.
        # We need to mock the query object to capture the filter/where calls and their arguments.
        pass # The actual assertion will inspect the mock object after JobQueryBuilder methods are called

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

# Assuming JobQueryBuilder takes a query object and modifies it
# We'll need a mock for the 'Job' model or whatever the query is built upon
class MockJobModel:
    # Define attributes that JobQueryBuilder might access, e.g., columns
    # For keyword search, it likely uses a text column, let's call it 'description'
    description = text("description") # Mock a column access

# Now, let's write the test cases using the refined mock

# We no longer need a fixture to create a JobQueryBuilder instance,
# as we import the singleton instance directly.

def test_single_word_keyword_search():
    # We don't need a mock query object for this test, as we are testing
    # the build_filter_conditions method which returns clauses and params,
    # not modifies a query object.
    keywords = ["business"]
    
    # Call the method that builds filter conditions
    where_clauses, query_params = job_query_builder.build_filter_conditions(
        keywords=keywords
    )

    # Now, inspect the returned clauses and parameters
    # We expect one clause for a single keyword, using ILIKE.
    
    assert len(where_clauses) > 0, "Expected at least one WHERE clause for keywords"
    
    # Check the first WHERE clause (assuming keywords are processed first)
    # The exact structure depends on the JobQueryBuilder implementation
    # It should be a string like "(j.title ILIKE '%%' || %s || '%%' OR j.description ILIKE '%%' || %s || '%%')"
    
    # Updated assertion to expect 2 clauses (embedding IS NOT NULL and keyword clause)
    assert len(where_clauses) == 2
    # Get the keyword clause (second clause)
    clause = where_clauses[1]
    
    assert isinstance(clause, str)
    assert "(j.title ILIKE '%%' || %s || '%%' OR j.description ILIKE '%%' || %s || '%%')" in clause

    # Check the parameters added
    # Expect two parameters for the single keyword (title and description)
    assert len(query_params) == 2
    assert query_params[0] == 'business'
    assert query_params[1] == 'business'

# Let's refine the MockQuery to capture filter/where calls
class MockColumn:
    def __init__(self, name):
        self.name = name
        self._method_calls = []

    def ilike(self, *args, **kwargs):
        self._method_calls.append(('ilike', args, kwargs))
        return text(f"{self.name} ILIKE :param") # Return a text object for the clause representation

    def __eq__(self, other):
         # Needed for comparisons in filter/where calls if JobQueryBuilder does `column == value`
         self._method_calls.append(('eq', (other,), {}))
         return text(f"{self.name} = :param")

    def get_method_calls(self):
        return self._method_calls

class MockJobModelRefined:
    def __init__(self):
        self.description = MockColumn("description")
        # Add other columns if needed by JobQueryBuilder

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
# We no longer need this fixture as we are using the singleton instance.
# @pytest.fixture
# def query_builder_refined():
#     mock_session = MockSession()
#     return JobQueryBuilder(mock_session, MockJobModelRefined())

# The refined test cases are also no longer needed as the original test cases
# have been updated to use the singleton instance and the correct method.
# Removing the refined test cases.

def test_multi_word_phrase_search():
    # We don't need a mock query object for this test.
    keywords = ["business account manager"]
    
    where_clauses, query_params = job_query_builder.build_filter_conditions(
        keywords=keywords
    )

    # Expect the 'embedding IS NOT NULL' clause and one phrase clause.
    assert len(where_clauses) == 2, "Expected two WHERE clauses (embedding and phrase)"
    
    phrase_clause = where_clauses[1]
    
    assert isinstance(phrase_clause, str)
    # The clause should contain the exact phrase search logic
    assert "(j.title ILIKE '%%' || %s || '%%' OR j.description ILIKE '%%' || %s || '%%')" in phrase_clause

    # Check the parameters
    assert len(query_params) == 2
    assert query_params[0] == 'business account manager'
    assert query_params[1] == 'business account manager'

def test_multiple_individual_words_as_potential_phrase():
    # We don't need a mock query object for this test.
    keywords = ["business", "account", "manager"]
    
    where_clauses, query_params = job_query_builder.build_filter_conditions(
        keywords=keywords
    )

    # Expect the 'embedding IS NOT NULL' clause and one combined WHERE clause with OR conditions
    assert len(where_clauses) == 2, "Expected two WHERE clauses (embedding and combined keywords)"
    
    combined_clause = where_clauses[1]
    
    assert isinstance(combined_clause, str)
    
    # Check for the presence of both phrase and individual word conditions in the clause string
    clause_str = str(combined_clause)
    assert "(j.title ILIKE '%%' || %s || '%%' OR j.description ILIKE '%%' || %s || '%%')" in clause_str
    assert " OR " in clause_str # Should be combined with OR

    # Check the parameters
    # Expect parameters for the phrase and each individual word (twice each)
    assert len(query_params) == 8 # 2 for phrase + 2*3 for individual words
    assert query_params[0] == 'business account manager'
    assert query_params[1] == 'business account manager'
    assert query_params[2] == 'business'
    assert query_params[3] == 'business'
    assert query_params[4] == 'account'
    assert query_params[5] == 'account'
    assert query_params[6] == 'manager'
    assert query_params[7] == 'manager'

class MockColumn:
    def __init__(self, name):
        self.name = name
        self._method_calls = []

    def ilike(self, *args, **kwargs):
        self._method_calls.append(('ilike', args, kwargs))
        return text(f"{self.name} ILIKE :param") # Return a text object for the clause representation

    def __eq__(self, other):
         # Needed for comparisons in filter/where calls if JobQueryBuilder does `column == value`
         self._method_calls.append(('eq', (other,), {}))
         return text(f"{self.name} = :param")

    def get_method_calls(self):
        return self._method_calls

class MockJobModelRefined:
    def __init__(self):
        self.description = MockColumn("description")
        # Add other columns if needed by JobQueryBuilder

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
    # JobQueryBuilder is a class that doesn't take arguments in its constructor
    return JobQueryBuilder()

# Remove all tests that use the non-existent build_query method