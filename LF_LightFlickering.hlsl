float seed = sin(Time * 13.37) * 43758.5453;
float noise = frac(sin(seed) * 10000.0);

//To introduce pseudo-randomness

float sineA = sin(Time * FlickerSpeed + noise * 2) * 0.5;
float sineB = sin(Time * FlickerSpeed * 1.27 + noise * 3) * 0.3;
float sineC = sin(Time * FlickerSpeed * 2.89 + noise * 5) * 0.2;

float flicker = sineA + sineB + sineC;

//Normalise

flicker = (flicker + 1) * 0.5;

//To break loop

float chaos = frac(sin(dot(float2(Time, noise), float2(12.9898, 78.233))) * 43758.5453);
float modulation = lerp(0.8, 1.2, chaos);

flicker *= modulation;
return saturate(flicker);



