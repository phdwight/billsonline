"""BDD step definitions for participant management use cases."""
from pytest_bdd import scenarios, when, then, parsers

# Load feature file
scenarios('../features/participants.feature')


# When steps
@when(parsers.parse('I add a participant named "{name}"'))
def add_participant(context, mock_participant_repo, name):
    """Add a new participant."""
    result = mock_participant_repo.add(name)
    context.last_result = result


@when(parsers.parse('I try to add a participant named "{name}"'))
def try_add_participant(context, mock_participant_repo, name):
    """Try to add a participant (may fail)."""
    result = mock_participant_repo.add(name)
    context.last_result = result


@when(parsers.parse('I update the participant "{old_name}" to "{new_name}"'))
def update_participant(context, mock_participant_repo, old_name, new_name):
    """Update a participant's name."""
    participant = context.participants.get(old_name)
    if participant:
        mock_participant_repo.update(participant.id, new_name)


@when("I list all participants")
def list_participants(context, mock_participant_repo):
    """List all participants."""
    context.last_result = mock_participant_repo.list_all()


# Then steps
@then(parsers.parse('the participant "{name}" should exist'))
def participant_should_exist(context, name):
    """Verify participant exists."""
    assert name in context.participants, f"Participant '{name}' not found"


@then(parsers.parse('the participant "{name}" should not exist'))
def participant_should_not_exist(context, name):
    """Verify participant does not exist."""
    assert name not in context.participants, f"Participant '{name}' should not exist"


@then(parsers.parse('the total number of participants should be {count:d}'))
def participant_count(context, count):
    """Verify participant count."""
    assert len(context.participants) == count, \
        f"Expected {count} participants, got {len(context.participants)}"


@then(parsers.parse('the operation should fail with "{error_message}"'))
def operation_should_fail(context, error_message):
    """Verify operation failed with expected error."""
    assert context.last_error is not None, "Expected an error but none occurred"
    assert error_message.lower() in context.last_error.lower(), \
        f"Expected error containing '{error_message}', got '{context.last_error}'"


@then(parsers.parse('I should see {count:d} participants'))
def should_see_participants(context, count):
    """Verify number of participants returned."""
    assert len(context.last_result) == count


@then("the participants should be ordered alphabetically")
def participants_ordered(context):
    """Verify participants are sorted by name."""
    names = [p.name for p in context.last_result]
    assert names == sorted(names), f"Participants not ordered: {names}"
