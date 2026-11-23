# API keys do not work on SND instances, and this feature authenticates with one.
# transform-staging and transform-prod do not serve the partition API.
@platform @freq-hourly @skip-snd @skip-transform-staging @skip-transform-prod
Feature: Partition a document
  As an API client
  I want to send a PDF to the partition API
  So that I get its content back as structured elements

  Scenario: A partitioned PDF comes back as elements headed by its title
    Given an API client with a valid Unstructured API key
    When the API client partitions the LayoutParser paper PDF with the "fast" strategy
    Then the partition API returns a list of document elements
    And the first element is titled "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
