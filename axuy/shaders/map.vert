#version 330

// https://gist.github.com/mikhailov-work/0d177465a8151eb6ede1768d51d476c7
const vec4 RED4 = vec4(0.13572138, 4.61539260, -42.66032258, 132.13108234);
const vec4 GREEN4 = vec4(0.09140261, 2.19418839, 4.84296658, -14.18503333);
const vec4 BLUE4 = vec4(0.10667330, 12.64194608, -60.58204836, 110.36276771);
const vec2 RED2 = vec2(-152.94239396, 59.28637943);
const vec2 GREEN2 = vec2(4.27729857, 2.82956604);
const vec2 BLUE2 = vec2(-89.90310912, 27.34824973);

uniform float visibility;
uniform mat4 mvp;

in vec3 in_vert;
out vec3 color;

vec3 turbo_colormap(in float x)
{
	vec4 v4 = vec4(1.0, x, x * x, x * x * x);
	vec2 v2 = v4.zw * v4.z;
	return vec3(dot(v4, RED4) + dot(v2, RED2),
	            dot(v4, GREEN4) + dot(v2, GREEN2),
	            dot(v4, BLUE4) + dot(v2, BLUE2));
}

void main()
{
	gl_Position = mvp * vec4(in_vert, 1.0);
	color = turbo_colormap(1 / (1 + pow(1 - gl_Position.z, 2)));
}
