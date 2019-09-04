#version 330

uniform vec3 color;

in float intensity;

void main()
{
	gl_FragColor = vec4(color * intensity, 1.0);
}
