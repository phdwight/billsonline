Feature: Bill Calculator
  As a billing system
  I want to calculate bill contributions correctly
  So that participants pay fair shares based on usage and split methods

  Background:
    Given the calculator is initialized

  # Basic Distribution Tests
  Scenario: Calculate basic electricity distribution by usage
    Given participants "Alice, Bob, Cara" exist
    And meter readings:
      | participant | current | previous |
      | Alice       | 200     | 100      |
      | Bob         | 150     | 100      |
      | Cara        | 100     | 100      |
    And a component "Electricity" with amount 300.00 split by "usage"
    When contributions are calculated
    Then electricity shares should be:
      | participant | amount |
      | Alice       | 200.00 |
      | Bob         | 100.00 |
      | Cara        | 0.00   |

  Scenario: Calculate water split equally among participants
    Given participants "Alice, Bob, Cara" exist
    And a component "Water" with amount 100.00 split by "equal"
    When contributions are calculated
    Then water shares should be approximately equal totaling 100.00

  Scenario: Calculate internet split equally among participants
    Given participants "Alice, Bob, Cara" exist
    And a component "Internet" with amount 80.00 split by "equal"
    When contributions are calculated
    Then internet shares should be approximately equal totaling 80.00

  Scenario: Zero total usage results in zero electricity shares
    Given participants "A, B" exist
    And meter readings:
      | participant | current | previous |
      | A           | 100     | 100      |
      | B           | 200     | 200      |
    And a component "Electricity" with amount 300.00 split by "usage"
    And a component "Water" with amount 90.00 split by "equal"
    And a component "Internet" with amount 60.00 split by "equal"
    When contributions are calculated
    Then all participants should have 0.00 for "Electricity"
    And all participants should have 45.00 for "Water"
    And all participants should have 30.00 for "Internet"

  # Dynamic Component Tests
  Scenario: Dynamic component with usage and equal split
    Given participants "Alice, Bob, Cara" exist
    And meter readings:
      | participant | current | previous |
      | Alice       | 200     | 100      |
      | Bob         | 150     | 100      |
      | Cara        | 100     | 100      |
    And a component "Electricity" with amount 300.00 split by "usage"
    And a component "Water" with amount 90.00 split by "equal"
    When contributions are calculated
    Then electricity shares should be:
      | participant | amount |
      | Alice       | 200.00 |
      | Bob         | 100.00 |
      | Cara        | 0.00   |
    And water shares should be:
      | participant | amount |
      | Alice       | 30.00  |
      | Bob         | 30.00  |
      | Cara        | 30.00  |

  Scenario: Dynamic component with percentage distribution
    Given participants "Alice, Bob, Cara" exist
    And a component "Gas" with amount 200.00 split by "percentage":
      | participant | percent |
      | Alice       | 50      |
      | Bob         | 30      |
      | Cara        | 20      |
    When contributions are calculated
    Then "Gas" shares should be:
      | participant | amount |
      | Alice       | 100.00 |
      | Bob         | 60.00  |
      | Cara        | 40.00  |

  Scenario: Dynamic component with fixed amount distribution
    Given participants "Alice, Bob, Cara" exist
    And a component "Trash" with amount 90.00 split by "amount":
      | participant | fixed |
      | Alice       | 20    |
      | Bob         | 30    |
      | Cara        | 40    |
    When contributions are calculated
    Then "Trash" shares should be:
      | participant | amount |
      | Alice       | 20.00  |
      | Bob         | 30.00  |
      | Cara        | 40.00  |

  # Rounding Correction Tests
  Scenario Outline: Rounding correction preserves total amount
    Given participants "<participants>" exist
    And a component "<component>" with amount <amount> split by "<split_method>"
    When contributions are calculated
    Then the sum of all "<component>" contributions should equal <amount>

    Examples:
      | participants   | component | amount | split_method |
      | A, B, C        | Equal100  | 100.00 | equal        |
      | A, B, C        | Water     | 90.00  | equal        |
      | Alice, Bob     | Internet  | 100.00 | equal        |

  Scenario: Equal split rounding produces correct distribution
    Given participants "A, B, C" exist
    And a component "Equal100" with amount 100.00 split by "equal"
    When contributions are calculated
    Then the "Equal100" shares sorted should be "33.33, 33.33, 33.34"

  Scenario: Usage split rounding produces correct distribution
    Given participants "A, B, C" exist
    And meter readings:
      | participant | current | previous |
      | A           | 101     | 100      |
      | B           | 201     | 200      |
      | C           | 301     | 300      |
    And a component "Usage100" with amount 100.00 split by "usage"
    When contributions are calculated
    Then the "Usage100" shares sorted should be "33.33, 33.33, 33.34"

  Scenario: Percentage distribution normalizes when not summing to 100
    Given participants "A, B, C" exist
    And a component "Percenty" with amount 100.00 split by "percentage":
      | participant | percent |
      | A           | 50      |
      | B           | 40      |
      | C           | 20      |
    When contributions are calculated
    Then the sum of all "Percenty" contributions should equal 100.00
    And "Percenty" shares should be approximately:
      | participant | amount |
      | A           | 45.45  |
      | B           | 36.36  |
      | C           | 18.18  |

  # Zero and Redistribution Tests
  Scenario Outline: Zero participant share and redistribute
    Given participants "Alice, Bob, Charlie" exist
    And a component "Shared" with amount <amount> split by "equal"
    When I zero out <zeroed>'s share of "Shared"
    And contributions are calculated
    Then <zeroed> should pay 0.00 for "Shared"
    And the component total should remain <amount>

    Examples:
      | amount | zeroed  |
      | 300.00 | Alice   |
      | 90.00  | Bob     |
      | 90.00  | Charlie |

  Scenario: Zero electricity by usage redistributes to rest
    Given participants "A, B, C" exist
    And meter readings:
      | participant | current | previous |
      | A           | 200     | 100      |
      | B           | 150     | 100      |
      | C           | 100     | 100      |
    And a component "Electricity" with amount 300.00 split by "usage"
    When I zero out A's share of "Electricity"
    And contributions are calculated
    Then "Electricity" shares should be:
      | participant | amount |
      | A           | 0.00   |
      | B           | 300.00 |
      | C           | 0.00   |

  Scenario: Zero water even split then redistribute
    Given participants "A, B, C" exist
    And a component "Water" with amount 90.00 split by "equal"
    When I zero out B's share of "Water"
    And contributions are calculated
    Then "Water" shares should be:
      | participant | amount |
      | A           | 45.00  |
      | B           | 0.00   |
      | C           | 45.00  |

  Scenario: Zero with 100% redistribution to one participant
    Given participants "Alice, Bob, Cara" exist
    And a component "Water" with amount 90.00 split by "equal"
    When I zero out Cara's share of "Water" with percent redistribution:
      | target | percent |
      | Alice  | 100     |
    And contributions are calculated
    Then "Water" shares should be:
      | participant | amount |
      | Alice       | 60.00  |
      | Bob         | 30.00  |
      | Cara        | 0.00   |

  # Custom Redistribution Tests
  Scenario: Percent redistribution with custom targets
    Given participants "Alice, Bob, Charlie" exist
    And a component "Water" with amount 120.00 split by "equal"
    When I zero out Bob's share of "Water" with percent redistribution:
      | target  | percent |
      | Alice   | 70      |
      | Charlie | 30      |
    And contributions are calculated
    Then "Water" shares should be:
      | participant | amount |
      | Alice       | 68.00  |
      | Bob         | 0.00   |
      | Charlie     | 52.00  |

  Scenario: Amount redistribution with overflow normalized
    Given participants "Alice, Bob" exist
    And a component "Internet" with amount 100.00 split by "equal"
    When I zero out Alice's share of "Internet" with amount redistribution:
      | target | amount |
      | Bob    | 60     |
    And contributions are calculated
    Then "Internet" shares should be:
      | participant | amount |
      | Alice       | 0.00   |
      | Bob         | 100.00 |

  Scenario: Self redistribution with percent
    Given participants "Alice, Bob, Charlie" exist
    And a component "Internet" with amount 90.00 split by "equal"
    When I zero out Alice's share of "Internet" with percent redistribution:
      | target  | percent |
      | Alice   | 50      |
      | Bob     | 30      |
      | Charlie | 20      |
    And contributions are calculated
    Then "Internet" shares should be:
      | participant | amount |
      | Alice       | 15.00  |
      | Bob         | 39.00  |
      | Charlie     | 36.00  |

  # Edge Cases
  Scenario: Multiple zeroed participants same component
    Given participants "Alice, Bob, Charlie" exist
    And a component "Water" with amount 90.00 split by "equal"
    When I zero out Alice's share of "Water" with percent redistribution:
      | target | percent |
      | Bob    | 100     |
    And I zero out Charlie's share of "Water" with percent redistribution:
      | target | percent |
      | Bob    | 100     |
    And contributions are calculated
    Then "Water" shares should be:
      | participant | amount |
      | Alice       | 0.00   |
      | Bob         | 90.00  |
      | Charlie     | 0.00   |

  Scenario: Empty targets treated as equal split
    Given participants "Alice, Bob, Cara, Dave" exist
    And a component "Water" with amount 80.00 split by "equal"
    When I zero out Dave's share of "Water" with no redistribution targets
    And contributions are calculated
    Then Dave should pay 0.00 for "Water"
    And the remaining participants should split the redistributed amount equally

  Scenario: Zero usage electricity with zero flag has no effect
    Given participants "Alice, Bob" exist
    And meter readings:
      | participant | current | previous |
      | Alice       | 100     | 100      |
      | Bob         | 200     | 200      |
    And a component "Electricity" with amount 50.00 split by "usage"
    When I zero out Alice's share of "Electricity"
    And contributions are calculated
    Then all participants should have 0.00 for "Electricity"

  Scenario: Amount underflow leftover split equally
    Given participants "Alice, Bob" exist
    And a component "Internet" with amount 100.00 split by "equal"
    When I zero out Alice's share of "Internet" with amount redistribution:
      | target | amount |
      | Bob    | 10     |
    And contributions are calculated
    Then "Internet" shares should be:
      | participant | amount |
      | Alice       | 0.00   |
      | Bob         | 100.00 |

  Scenario: Percentage with zero and amount redistribution mode
    Given participants "Alice, Bob, Cara" exist
    And a component "Fuel" with amount 100.00 split by "percentage":
      | participant | percent |
      | Alice       | 70      |
      | Bob         | 20      |
      | Cara        | 10      |
    When I zero out Cara's share of "Fuel" with amount redistribution:
      | target | amount |
      | Alice  | 10     |
    And contributions are calculated
    Then the sum of all "Fuel" contributions should equal 100.00
