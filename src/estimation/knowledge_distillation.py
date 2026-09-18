"""Teacher-student knowledge distillation loss for edge model compression.

Tactical use: a massive cloud-trained threat-detection model cannot run in
real time on an edge drone. Distillation trains a small student model to
match both the ground-truth labels and the teacher's softened output
distribution, transferring the teacher's learned decision boundaries into
a sub-millisecond edge-deployable model.
"""

import numpy as np

from src.utils.math_utils import softmax


class DistillationLoss:
    """Computes the combined cross-entropy + KL-divergence distill loss."""

    def __init__(self, alpha=0.5, temperature=2.0):
        """Set the CE/KL blend weight alpha and softening temperature tau."""
        self.alpha = alpha
        self.temperature = temperature

    def calc_cross_entropy(self, true_labels, student_logits):
        """Evaluate CE(y, student_logits) for a batch of integer class labels.

        Tactical advantage: vectorized over the full batch via fancy
        indexing, giving the ground-truth training signal in one pass.
        """
        probabilities = softmax(student_logits)
        labels = np.asarray(true_labels, dtype=np.int64)
        sample_index = np.arange(labels.shape[0])
        true_class_probability = probabilities[sample_index, labels]
        return -np.log(np.clip(true_class_probability, 1e-12, None))

    def calc_kl_divergence(self, teacher_logits, student_logits):
        """Evaluate KL(softmax(teacher/tau) || softmax(student/tau)).

        Tactical advantage: transfers the teacher's full softened output
        distribution (its relative confidence across all classes, not
        just the top label) into the student in one vectorized pass.
        """
        teacher_probs = softmax(teacher_logits / self.temperature)
        student_probs = softmax(student_logits / self.temperature)
        safe_teacher = np.clip(teacher_probs, 1e-12, None)
        safe_student = np.clip(student_probs, 1e-12, None)
        return np.sum(
            safe_teacher * (np.log(safe_teacher) - np.log(safe_student)),
            axis=-1,
        )

    def calc_total_loss(self, true_labels, teacher_logits, student_logits):
        """Evaluate the full blended distillation loss for a training batch.

        Tactical advantage: a single call yields the per-sample training
        signal used to compress a cloud-scale model into an edge-ready
        student, balancing ground-truth accuracy against teacher mimicry.
        """
        cross_entropy = self.calc_cross_entropy(true_labels, student_logits)
        kl_divergence = self.calc_kl_divergence(
            teacher_logits, student_logits
        )
        total = (
            self.alpha * cross_entropy
            + (1.0 - self.alpha) * (self.temperature ** 2) * kl_divergence
        )
        return {
            "cross_entropy": cross_entropy,
            "kl_divergence": kl_divergence,
            "total_loss": total,
        }
