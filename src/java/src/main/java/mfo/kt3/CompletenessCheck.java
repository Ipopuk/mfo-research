package mfo.kt3;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class CompletenessCheck {
    public record Input(String applicationId, Map<String, Map<String, Object>> fields,
                        Map<String, Document> documents, List<ApplicationDocument> links) {}

    public record Result(List<String> missingFields, List<String> missingDocuments) {
        public Result {
            missingFields = List.copyOf(missingFields);
            missingDocuments = List.copyOf(missingDocuments);
        }

        public boolean complete() { return missingFields.isEmpty() && missingDocuments.isEmpty(); }
    }

    public Result check(Input input, List<CompletenessRule> rules) {
        List<String> missingFields = new ArrayList<>();
        List<String> missingDocuments = new ArrayList<>();
        for (CompletenessRule rule : rules) {
            rule.inspect(input).ifPresent(missing -> {
                switch (missing.category()) {
                    case FIELD -> missingFields.add(missing.name());
                    case DOCUMENT -> missingDocuments.add(missing.name());
                }
            });
        }
        return new Result(missingFields, missingDocuments);
    }
}
