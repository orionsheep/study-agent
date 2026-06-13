export type WorkEnergyInput = {
  mass: number;
  initialVelocity: number;
  finalVelocity: number;
  force: number;
  displacement: number;
};

export function workEnergy(values: WorkEnergyInput) {
  const initialKinetic = 0.5 * values.mass * values.initialVelocity ** 2;
  const finalKinetic = 0.5 * values.mass * values.finalVelocity ** 2;
  const deltaKinetic = finalKinetic - initialKinetic;
  const work = values.force * values.displacement;
  return { initialKinetic, finalKinetic, deltaKinetic, work, difference: work - deltaKinetic };
}

export type GradientPoint = {
  iteration: number;
  x: number;
  loss: number;
};

export function gradientDescent(learningRate: number, initialPoint: number, iterations: number): GradientPoint[] {
  const points: GradientPoint[] = [];
  let x = initialPoint;
  for (let iteration = 0; iteration <= iterations; iteration += 1) {
    points.push({ iteration, x, loss: x ** 2 });
    const grad = 2 * x;
    x = x - learningRate * grad;
  }
  return points;
}

export function isLearningRateUnstable(learningRate: number) {
  return learningRate >= 1;
}
