"""Shared defense metadata constants; safe to import in a standard-library-only deploy."""
FORMULA='100 * sum(opponent points) / sum(opponent FGA + 0.4 * FTA - ORB + totalTurnovers)'
METRIC='estimated_defensive_rating'
