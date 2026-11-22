package mfo.kt3;

import java.math.BigDecimal;

public record Application(String id, String applicantId, BigDecimal amount,
                          Integer termMonths, String status, String receivedAt) {}
