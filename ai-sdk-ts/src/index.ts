import { z } from "zod";

export const weatherArgs = z.object({ city: z.string() });

// Placeholder tool executor; real AI SDK Core wiring comes later.
export function mockGetWeather(args: z.infer<typeof weatherArgs>) {
  return { city: args.city, temp_c: 18, conditions: "cloudy" };
}
