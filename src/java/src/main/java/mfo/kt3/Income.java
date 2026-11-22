package mfo.kt3;

import java.math.BigDecimal;

public record Income(String id, String applicantId, BigDecimal monthlyAmount, boolean verified) {}
