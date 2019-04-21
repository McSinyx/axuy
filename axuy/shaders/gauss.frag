#version 330

const float coeffs[13] = float[](
	0.002406, 0.009255, 0.027867, 0.065666, 0.121117, 0.174868, 0.197641,
	0.174868, 0.121117, 0.065666, 0.027867, 0.009255, 0.002406);

uniform sampler2D tex;

in vec2 coords[13];
out vec4 f_color;

void main(void)
{
	f_color = vec4(0.0);
	for (int i = 0; i < 13; ++i)
		f_color += texture(tex, coords[i]) * coeffs[i];
}
