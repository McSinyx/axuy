#version 330

#define SQR(x) ((x) * (x))

uniform float abrtn;
uniform float zoom;
uniform sampler2D la;
uniform sampler2D tex;

in vec2 in_text;

vec2 barrel(vec2 vert)
{
	float coef = 1.0 + (SQR(vert.x) + SQR(vert.y)) * zoom;
	return vert * coef * (0.5 - zoom) + 0.5;
}

vec2 fringe(vec2 vert, float delta)
{
	return vec2(pow(abs(vert.x), 1.0 + delta) * sign(vert.x),
	            pow(abs(vert.y), 1.0 + delta) * sign(vert.y)) * 0.5 + 0.5;
}

void main(void)
{
	vec2 text = barrel(in_text * 2.0 - 1.0);
	vec2 vert = text * 2.0 - 1.0;

	gl_FragColor = texture(la, text) + vec4(
		texture(tex, fringe(vert, -abrtn)).r,
		texture(tex, fringe(vert, abrtn)).g,
		texture(tex, text).b, 1.0);
}
