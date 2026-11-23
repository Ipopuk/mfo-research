package mfo.kt3;

import java.util.Optional;

public interface CompletenessRule {
    enum Category { FIELD, DOCUMENT }

    record Missing(Category category, String name) {}

    Optional<Missing> inspect(CompletenessCheck.Input input);
}
