package mfo.kt3;

import java.util.Objects;
import java.util.Optional;

public record RequiredDocument(String kind) implements CompletenessRule {
    @Override
    public Optional<Missing> inspect(CompletenessCheck.Input input) {
        for (ApplicationDocument link : input.links()) {
            if (!Objects.equals(link.applicationId(), input.applicationId())) {
                continue;
            }
            Document document = input.documents().get(link.documentId());
            if (document != null && Objects.equals(kind, document.kind()) && document.valid()) {
                return Optional.empty();
            }
        }
        return Optional.of(new Missing(Category.DOCUMENT, kind));
    }
}
