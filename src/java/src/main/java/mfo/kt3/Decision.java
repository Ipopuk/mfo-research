package mfo.kt3;

import java.math.BigDecimal;

public abstract sealed class Decision permits Approval, Refusal {
    private final String id;
    private final String applicationId;
    private final String employeeId;
    private final String reason;

    protected Decision(String id, String applicationId, String employeeId, String reason) {
        this.id = id;
        this.applicationId = applicationId;
        this.employeeId = employeeId;
        this.reason = reason;
    }

    public String id() { return id; }
    public String applicationId() { return applicationId; }
    public String employeeId() { return employeeId; }
    public String reason() { return reason; }

    public abstract String outcome();
    public abstract BigDecimal approvedAmount();
    public abstract Integer approvedTermMonths();
}
