#version 330

uniform float invfov;
uniform sampler2D la;
uniform sampler2D tex;

in vec2 in_text;
out vec4 f_color;

vec2 fringe(vec2 vert, float delta)
{
	return vec2(pow(abs(vert.x), 1.0 + delta) * sign(vert.x),
	            pow(abs(vert.y), 1.0 + delta) * sign(vert.y)) * 0.5 + 0.5;
}

void main(void)
{
	vec2 vert = in_text * 2.0 - 1.0;
	f_color = texture(la, in_text) + vec4(
		texture(tex, fringe(vert, -invfov)).r,
		texture(tex, fringe(vert, invfov)).g,
		texture(tex, in_text).b, 1.0);
}
