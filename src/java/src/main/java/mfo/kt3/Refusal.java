package mfo.kt3;

import java.math.BigDecimal;

public final class Refusal extends Decision {
    public Refusal(String id, String applicationId, String employeeId, String reason) {
        super(id, applicationId, employeeId, reason);
        if (reason == null || reason.isEmpty()) {
            throw new IllegalArgumentException("Для отказа требуется основание");
        }
    }

    @Override public String outcome() { return "refused"; }
    @Override public BigDecimal approvedAmount() { return null; }
    @Override public Integer approvedTermMonths() { return null; }
}
