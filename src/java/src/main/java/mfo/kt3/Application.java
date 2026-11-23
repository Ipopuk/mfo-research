package mfo.kt3;

import java.math.BigDecimal;
import java.util.Set;

public record Application(String id, String applicantId, BigDecimal amount,
                          Integer termMonths, String status, String receivedAt) {
    private static final Set<String> FINAL_STATUSES = Set.of("approved", "refused", "withdrawn");

    public record DecisionEntry(Application application, Decision decision) {}

    public DecisionEntry recordDecision(String decisionId, String employeeId, String outcome,
                                        String reason, BigDecimal approvedAmount,
                                        Integer approvedTermMonths) {
        if (status != null && FINAL_STATUSES.contains(status)) {
            throw new IllegalArgumentException("У завершённой заявки уже есть итоговый статус");
        }
        if (employeeId == null || employeeId.isEmpty()) {
            throw new IllegalArgumentException("Не указан уполномоченный сотрудник");
        }
        Decision decision = switch (outcome) {
            case "approved" -> new Approval(decisionId, id, employeeId, reason, approvedAmount, approvedTermMonths);
            case "refused" -> new Refusal(decisionId, id, employeeId, reason);
            case null, default -> throw new IllegalArgumentException("Допустимы только одобрение и отказ");
        };
        Application updated = new Application(id, applicantId, amount, termMonths, decision.outcome(), receivedAt);
        return new DecisionEntry(updated, decision);
    }
}
