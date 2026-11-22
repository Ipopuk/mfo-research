package mfo.kt3;

public record CheckResult(String id, String applicationId, String kind, String source,
                          String result, String checkedAt) {}
