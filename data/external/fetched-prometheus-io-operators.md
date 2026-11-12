---
title: "Operators"
failure_type: other
source_type: external_doc
source_url: https://prometheus.io/docs/prometheus/latest/querying/operators/
license: Apache-2.0
status: external
---

## Summary
PromQL supports unary, binary, and aggregation operators.

The only unary operator in PromQL is - (unary minus). It can be applied to a scalar or an instant vector. In the former case, it returns a scalar with inverted sign. In the latter case, it returns an instant vector with inverted sign for each element. The sign of a histogram sample is inverted by inverting the sign of all bucket populations and the count and the sum of observations. The resulting histogram sample is always considered a gauge histogram.

Binary operators cover basic logical and arithmetic operations. For operations between two instant vectors, the matching behavior can be modified.

The following binary arithmetic operators exist in PromQL:

Binary arithmetic operators are defined between scalar/scalar, vector/scalar, and vector/vector value pairs. They follow the usual IEEE 754 floating point arithmetic , including the handling of special values like NaN, +Inf, and -Inf.

Between two scalars, the behavior is straightforward: they evaluate to another scalar that is the result of the operator applied to both scalar operands.

## Reference
Full article / official documentation: https://prometheus.io/docs/prometheus/latest/querying/operators/
