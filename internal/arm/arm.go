package arm

import (
	"fmt"
	"os"
	"path/filepath"
)

type Arm struct {
	Name        string
	LoadoutPath string
}

func ParseArm(spec string) (*Arm, error) {
	if spec == "vanilla" {
		return &Arm{Name: "vanilla", LoadoutPath: ""}, nil
	}

	abs, err := filepath.Abs(spec)
	if err != nil {
		return nil, fmt.Errorf("resolve arm path %q: %w", spec, err)
	}

	info, err := os.Stat(abs)
	if err != nil {
		return nil, fmt.Errorf("arm path %q: %w", abs, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("arm path %q is not a directory", abs)
	}

	return &Arm{Name: filepath.Base(abs), LoadoutPath: abs}, nil
}
