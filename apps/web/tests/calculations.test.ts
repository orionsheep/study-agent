import { describe, expect, it } from "vitest";
import { gradientDescent, isLearningRateUnstable, workEnergy } from "../src/features/learning-apps/calculations";

describe("learning app calculations", () => {
  it("computes work-energy values", () => {
    const result = workEnergy({ mass: 2, initialVelocity: 3, finalVelocity: 7, force: 8, displacement: 5 });
    expect(result.work).toBe(40);
    expect(result.initialKinetic).toBe(9);
    expect(result.finalKinetic).toBe(49);
    expect(result.deltaKinetic).toBe(40);
    expect(result.difference).toBe(0);
  });

  it("generates gradient descent trajectory and unstable flag", () => {
    const stable = gradientDescent(0.2, 4, 4);
    expect(stable[0].loss).toBe(16);
    expect(stable[stable.length - 1].loss).toBeLessThan(16);
    expect(isLearningRateUnstable(0.2)).toBe(false);
    expect(isLearningRateUnstable(1.2)).toBe(true);
  });
});
