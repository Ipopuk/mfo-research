package mfo.kt3;

import java.math.BigDecimal;

public final class Approval extends Decision {
    private final BigDecimal amount;
    private final int termMonths;

    public Approval(String id, String applicationId, String employeeId, String reason,
                    BigDecimal amount, Integer termMonths) {
        super(id, applicationId, employeeId, reason);
        if (amount == null || amount.signum() <= 0 || termMonths == null || termMonths <= 0) {
            throw new IllegalArgumentException("Для одобрения нужны положительные сумма и срок");
        }
        this.amount = amount;
        this.termMonths = termMonths;
    }

    @Override public String outcome() { return "approved"; }
    @Override public BigDecimal approvedAmount() { return amount; }
    @Override public Integer approvedTermMonths() { return termMonths; }
}
